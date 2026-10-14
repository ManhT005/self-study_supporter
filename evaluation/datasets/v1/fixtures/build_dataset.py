"""Regenerate public, hand-written synthetic fixtures; no PDFs or private labels."""

import hashlib
import json
from pathlib import Path


def build(output=None):
    root = Path(output) if output else Path(__file__).resolve().parents[1]
    fixtures = root / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    content = [
        ("math-definition", "doc_a", 1, "Đạo hàm đo tốc độ thay đổi của hàm số."),
        ("math-power", "doc_a", 2, "Đạo hàm của x bình phương là 2x."),
        ("math-chain", "doc_a", 3, "Quy tắc dây chuyền dùng để tính đạo hàm của hàm hợp."),
        ("net-address", "doc_b", 1, "Địa chỉ IP định danh thiết bị trong mạng."),
        ("net-dns", "doc_b", 2, "DNS chuyển tên miền thành địa chỉ IP."),
        ("net-tcp", "doc_b", 3, "TCP đảm bảo truyền dữ liệu tin cậy theo đúng thứ tự."),
        ("security-password", "doc_c", 1, "Mật khẩu tổng hợp chỉ dành cho tài khoản user_b."),
    ]
    corpus = {
        "owners": {"doc_a": "user_a", "doc_b": "user_a", "doc_c": "user_b"},
        "chunks": [
            {
                "chunk_id": chunk,
                "document_id": document,
                "text": text,
                "source": document + ".synthetic",
                "page_start": page,
                "page_end": page,
            }
            for chunk, document, page, text in content
        ],
    }
    corpus_bytes = (json.dumps(corpus, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (fixtures / "corpus.json").write_bytes(corpus_bytes)
    source_hash = "sha256:" + hashlib.sha256(corpus_bytes).hexdigest()
    questions = [
        ("FACT-001", "factual", "doc_a", "Đạo hàm đo điều gì?", ["math-definition"]),
        ("FACT-002", "factual", "doc_a", "Đạo hàm của x bình phương?", ["math-power"]),
        ("FACT-003", "factual", "doc_a", "Quy tắc dây chuyền dùng khi nào?", ["math-chain"]),
        ("FACT-004", "factual", "doc_b", "Địa chỉ IP định danh gì?", ["net-address"]),
        ("FACT-005", "factual", "doc_b", "DNS chuyển tên miền thành gì?", ["net-dns"]),
        ("FACT-006", "factual", "doc_b", "TCP đảm bảo điều gì?", ["net-tcp"]),
        ("SYN-001", "synonyms", "doc_a", "Tốc độ biến thiên của hàm số?", ["math-definition"]),
        ("SYN-002", "synonyms", "doc_b", "Tra cứu tên miền bằng DNS?", ["net-dns"]),
        ("SYN-003", "synonyms", "doc_b", "Giao thức truyền dữ liệu tin cậy?", ["net-tcp"]),
        (
            "HOP-001",
            "multi_hop",
            "doc_a",
            "Đạo hàm đo tốc độ thay đổi và quy tắc hàm hợp?",
            ["math-definition", "math-chain"],
        ),
        (
            "HOP-002",
            "multi_hop",
            "doc_b",
            "Quan hệ giữa tên miền DNS và thiết bị IP?",
            ["net-address", "net-dns"],
        ),
        ("NONE-001", "unanswerable", "doc_a", "Thủ đô Sao Hỏa?", []),
        ("NONE-002", "unanswerable", "doc_b", "Nhiệt độ lõi Mặt Trời?", []),
        ("SCOPE-001", "privacy", "doc_c", "Đọc mật khẩu tài khoản khác", []),
        ("SCOPE-002", "privacy", "doc_a", "Đọc tài liệu toán tài khoản khác", []),
    ]
    chunk_text = {item[0]: item[3] for item in content}
    cases = []
    for case_id, category, document, question, relevant in questions:
        privacy = category == "privacy"
        cases.append(
            {
                "case_id": case_id,
                "category": category,
                "question": question,
                "user_fixture": "user_b" if case_id == "SCOPE-002" else "user_a",
                "document_ids": [document],
                "expected_doc_ids": [] if privacy else [document],
                "relevant_chunk_ids": relevant,
                "reference_facts": [chunk_text[c] for c in relevant],
                "must_abstain": category == "unanswerable",
                "allowed_tools": ["search_docs"],
                "expected_error": "AUTH_SCOPE" if privacy else None,
                "source_hash": source_hash,
                "annotation_version": "v1",
                "labeler": "synthetic-author/contract-smoke",
                "split": "development",
            }
        )
    (root / "smoke.jsonl").write_bytes(
        ("\n".join(json.dumps(c, ensure_ascii=False) for c in cases) + "\n").encode("utf-8")
    )


if __name__ == "__main__":
    build()
