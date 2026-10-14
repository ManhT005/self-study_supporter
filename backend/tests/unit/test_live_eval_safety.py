import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from evaluation.live.fixtures import SnapshotFixtures, payload_hashes, write_json
from evaluation.live.provider import PinnedGemini, RequestBudget
from evaluation.live.runner import LiveCallbacks
from study_supporter.domain.errors import QuotaExceeded
from study_supporter.domain.provider_errors import ProviderUnavailable


def fixture_snapshot(tmp_path):
    from backend.tests.unit.test_benchmark_labels import corpus_fixture

    root = tmp_path / "snapshot"
    root.mkdir()
    (root / "app.db").write_bytes(b"immutable offline payload")
    corpus = corpus_fixture().model_copy(update={"payload_hashes": payload_hashes(root)})
    write_json(root / "corpus.json", corpus.model_dump(mode="json"))
    return root


def test_leases_are_disjoint_and_writes_never_touch_the_snapshot(tmp_path):
    root = fixture_snapshot(tmp_path)
    fixture = SnapshotFixtures(root, tmp_path / "work")
    with fixture.lease() as first:
        (first / "app.db").write_bytes(b"variant A mutated")
        with fixture.lease() as second:
            assert (
                first != second and (second / "app.db").read_bytes() == b"immutable offline payload"
            )
    fixture.verify()
    assert not list((tmp_path / "work").iterdir())


def test_corrupt_snapshot_and_overlapping_work_root_are_rejected(tmp_path):
    root = fixture_snapshot(tmp_path)
    with pytest.raises(ValueError):
        SnapshotFixtures(root, root / "work")
    fixture = SnapshotFixtures(root, tmp_path / "work")
    (root / "corpus.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        fixture.verify()


def test_request_budget_counts_before_transport_and_stops_before_extra_call(tmp_path):
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(
        text="answer", usage_metadata=None, model_version="gemini-2.5-flash"
    )
    budget = RequestBudget(1, 60, tmp_path / "calls.jsonl")
    llm = PinnedGemini("gemini-2.5-flash", budget, api_key="test-only", client=client)
    assert llm.chat([{"role": "user", "content": "question"}]).usage is None
    config = client.models.generate_content.call_args.kwargs["config"]
    assert (
        config.max_output_tokens == 768
        and config.temperature == 0
        and config.thinking_config.thinking_budget == 0
    )
    with pytest.raises(ProviderUnavailable):
        llm.chat([{"role": "user", "content": "extra"}])
    assert client.models.generate_content.call_count == 1 and budget.calls == 1
    assert len((tmp_path / "calls.jsonl").read_text().splitlines()) == 1


def test_provider_429_is_sanitized_and_disables_further_attempts(tmp_path):
    class RateLimit(Exception):
        code = 429

    client = Mock()
    client.models.generate_content.side_effect = RateLimit("private-key-SECRET")
    llm = PinnedGemini(
        "gemini-2.5-flash",
        RequestBudget(6, 60, tmp_path / "calls.jsonl"),
        api_key="test-only",
        client=client,
    )
    with pytest.raises(QuotaExceeded) as failure:
        llm.chat([{"role": "user", "content": "question"}])
    assert "SECRET" not in str(failure.value)
    with pytest.raises(ProviderUnavailable):
        llm.chat([{"role": "user", "content": "another"}])
    assert client.models.generate_content.call_count == 1 and llm.budget.calls == 1
    assert llm.failure_http_status == 429 and llm.failure_type == "OTHER"


def test_provider_diagnostics_keep_status_without_private_exception_text(tmp_path):
    class ClientError(Exception):
        code = 400

    client = Mock()
    client.models.generate_content.side_effect = ClientError("private-key-SECRET private prompt")
    llm = PinnedGemini(
        "gemini-2.5-flash",
        RequestBudget(1, 60, tmp_path / "calls.jsonl"),
        api_key="test-only",
        client=client,
    )
    with pytest.raises(ProviderUnavailable) as failure:
        llm.chat([{"role": "user", "content": "question"}])
    assert str(failure.value) == "Provider request failed"
    assert llm.failure_http_status == 400 and llm.failure_type == "ClientError"
    assert llm.blocked and llm.budget.calls == 1


def test_flash_lite_31_pins_minimal_thinking_without_legacy_token_budget(tmp_path):
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(
        text="answer", usage_metadata=None, model_version="gemini-3.1-flash-lite"
    )
    llm = PinnedGemini(
        "gemini-3.1-flash-lite",
        RequestBudget(1, 60, tmp_path / "calls.jsonl"),
        api_key="test-only",
        client=client,
    )
    llm.chat([{"role": "user", "content": "question"}])
    thinking = client.models.generate_content.call_args.kwargs["config"].thinking_config
    assert thinking.thinking_level.value == "MINIMAL" and thinking.thinking_budget is None
    assert thinking.include_thoughts is False


def test_deadline_and_input_cap_do_not_reserve_a_cloud_request(tmp_path):
    times = iter([0, 10])
    budget = RequestBudget(6, 5, tmp_path / "calls.jsonl", clock=lambda: next(times))
    with pytest.raises(TimeoutError):
        budget.reserve()
    assert budget.calls == 0 and not budget.journal.exists()
    client = Mock()
    llm = PinnedGemini(
        "gemini-2.5-flash",
        RequestBudget(6, 60, tmp_path / "other.jsonl"),
        api_key="test-only",
        client=client,
    )
    with pytest.raises(ValueError):
        llm.chat([{"role": "user", "content": "x" * 24001}])
    client.models.generate_content.assert_not_called()


def test_sdk_transport_is_pinned_to_one_attempt_and_never_auto_falls_back(tmp_path, monkeypatch):
    from google import genai

    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(
        text="answer", usage_metadata=None, model_version=None
    )
    constructor = Mock(return_value=client)
    monkeypatch.setattr(genai, "Client", constructor)
    llm = PinnedGemini(
        "gemini-2.5-flash", RequestBudget(6, 60, tmp_path / "calls.jsonl"), api_key="test-only"
    )
    llm.chat([{"role": "user", "content": "question"}])
    assert constructor.call_args.kwargs["http_options"].retry_options.attempts == 1
    assert client.models.generate_content.call_args.kwargs["model"] == "gemini-2.5-flash"


def test_response_after_deadline_is_recorded_as_timeout_without_an_extra_request(tmp_path):
    ticks = iter([0, 0, 6])
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(
        text="late", usage_metadata=None, model_version="pinned"
    )
    llm = PinnedGemini(
        "gemini-2.5-flash",
        RequestBudget(1, 5, tmp_path / "calls.jsonl", clock=lambda: next(ticks)),
        api_key="test-only",
        client=client,
    )
    with pytest.raises(TimeoutError):
        llm.chat([{"role": "user", "content": "question"}])
    assert llm.budget.calls == 1 and llm.failure_reason == "DEADLINE_EXHAUSTED"


def test_blind_packets_hide_variant_labels_and_account_for_missing_answers(tmp_path):
    from evaluation.live.review_export import export_review
    from backend.tests.unit.test_benchmark_labels import corpus_fixture, case_fixture
    from evaluation.schema import EvaluationCase

    item = case_fixture(corpus_fixture())
    case = EvaluationCase.model_validate(
        {key: value for key, value in item.items() if key in EvaluationCase.model_fields}
    )
    output = tmp_path / "review"
    export_review(
        output,
        [case],
        [{"case_id": case.case_id, "variant": "legacy_react", "answer": "fixture", "evidence": []}],
    )
    packets = json.loads((output / "packets.private.json").read_text(encoding="utf-8"))
    assert "variant" not in packets[0]
    coverage = json.loads((output / "coverage.private.json").read_text(encoding="utf-8"))
    assert coverage["missing_answers"] == 1 and coverage["reviewed"] is False


def test_worker_timeout_preserves_request_accounting_and_metadata(tmp_path, monkeypatch):
    import subprocess
    from backend.tests.unit.test_benchmark_labels import case_fixture
    from evaluation.schema import EvaluationCase
    from evaluation.errors import EvaluationFailure

    fixture = SnapshotFixtures(fixture_snapshot(tmp_path), tmp_path / "work")
    item = case_fixture(fixture.corpus)
    case = EvaluationCase.model_validate(
        {key: value for key, value in item.items() if key in EvaluationCase.model_fields}
    )
    callbacks = LiveCallbacks(fixture, {"model": "gemini-2.5-flash"})

    def timeout(command, **kwargs):
        request = json.loads(
            Path(command[command.index("--input") + 1]).read_text(encoding="utf-8")
        )
        Path(request["journal"]).write_text('{"event":"model_call_reserved"}\n', encoding="utf-8")
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(EvaluationFailure) as failure:
        callbacks.variant("legacy_react")(case)
    assert failure.value.code == "TIMEOUT" and callbacks.calls == 1
    assert callbacks.telemetry[0]["failure_reason"] == "WORKER_TIMEOUT"
    assert not list((tmp_path / "work").iterdir())
