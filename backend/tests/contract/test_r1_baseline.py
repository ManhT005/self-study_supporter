import shutil

from scripts.profile_r1_baseline import run_profile
from scripts.verify_r1_baseline import ROOT, validate


def test_frozen_baseline_has_complete_requirement_ownership():
    assert validate() == []


def test_requirement_drift_cannot_silently_pass(tmp_path):
    for relative in ("docs/srs",):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    path = tmp_path / "docs/srs/requirements.json"
    path.write_text(
        path.read_text(encoding="utf-8").replace("AUTH-01", "AUTH-99"), encoding="utf-8"
    )
    errors = validate(tmp_path)
    assert any("Frozen asset drift" in error for error in errors)
    private_source = tmp_path / "source.md"
    private_source.write_text("No approved requirements here", encoding="utf-8")
    errors = validate(tmp_path, source=private_source)
    assert "Private source checksum mismatch" in errors
    assert "Private SRS and public registry ID sets differ" in errors


def test_offline_profile_exercises_hotspots_and_states_its_limits():
    report = run_profile(2)
    assert report["result"] == "SYNTHETIC_ONLY" and report["reviewer"] is None
    operations = {row["operation"] for row in report["records"]}
    assert operations == {
        "open_document",
        "load_all_chunks",
        "bm25_build",
        "embedding",
        "retrieval",
        "tool_round",
        "provider_generation",
        "ingestion",
        "pdf_parse",
    }
    for row in report["summary"]:
        assert row["samples"] > 0 and row["errors"] == 0
        assert 0 <= row["p50_ms"] <= row["p95_ms"]
    # Cold-session and reused-session measurements must remain distinguishable.
    builds = [row for row in report["records"] if row["operation"] == "bm25_build"]
    assert len(builds) == 2
    assert all(row["phase"] == "cold_session" for row in builds)
