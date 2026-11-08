"""Verify frozen artifacts and exact SRS requirement-to-package coverage offline."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {"FR": 96, "BR": 34, "NFR": 28, "UAT": 26, "UC": 14}
ID = re.compile(r"(?:AUTH|DOC|JOB|TUT|QUIZ|PRG|PLN|NOTE|HIS|NTF|AUT|DATA|OPS|BR|NFR|UAT)-\d{2}")


def validate(root=ROOT, source=None):
    manifest = json.loads((root / "docs/srs/baseline.json").read_text(encoding="utf-8"))
    errors = []
    for asset in manifest["assets"]:
        path = root / asset["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            errors.append(f"Frozen asset drift: {asset['path']}; approved CR required")
    registry = json.loads((root / "docs/srs/requirements.json").read_text(encoding="utf-8"))
    records = registry["requirements"]
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate requirement ID")
    if registry["counts"] != COUNTS or any(
        sum(record["category"] == category for record in records) != count
        for category, count in COUNTS.items()
    ):
        errors.append("SRS category counts drift")
    if source is not None:
        data = source.read_bytes()
        if source.suffix.lower() == ".docx":
            expected_hash = manifest["source"]["sha256"]
            from zipfile import ZipFile
            from xml.etree import ElementTree

            with ZipFile(source) as archive:
                document = ElementTree.fromstring(archive.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            source_ids = set()
            for row in document.findall(".//w:tr", ns):
                cell = row.find("w:tc", ns)
                key = "".join(cell.itertext()) if cell is not None else ""
                if ID.fullmatch(key.strip()):
                    source_ids.add(key.strip())
            for paragraph in document.findall(".//w:p", ns):
                text = "".join(paragraph.itertext())
                match = re.match(r"^(UC-\d{2}) —", text)
                if match:
                    source_ids.add(match.group(1))
        else:
            expected_hash = next(
                asset["sha256"]
                for asset in manifest["private_source_checksums"]
                if asset["filename"] == "SSS-SRS-001_v1.0.md"
            )
            text = data.decode("utf-8")
            source_ids = set(re.findall(r"^\| (" + ID.pattern + r") \|", text, re.MULTILINE))
            source_ids.update(re.findall(r"^(UC-\d{2}) —", text, re.MULTILINE))
        if hashlib.sha256(data).hexdigest() != expected_hash:
            errors.append("Private source checksum mismatch")
        if source_ids != set(ids):
            errors.append("Private SRS and public registry ID sets differ")
    for record in records:
        if not re.fullmatch(r"WP-(?:0[1-9]|1[0-9]|2[01])", record["work_package"] or ""):
            errors.append(f"Missing/invalid package: {record['id']}")
        if record["status"] != "PLANNED" or record["reviewer"] is not None:
            errors.append(f"Frozen registry cannot claim acceptance: {record['id']}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, help="Authorized private Word or frozen Markdown source"
    )
    args = parser.parse_args()
    errors = validate(source=args.source)
    if errors:
        raise SystemExit("\n".join(errors))
    print("R1 public ID registry verified: 96 FR, 34 BR, 28 NFR, 26 UAT, 14 UC")
    print(
        "Private source verified"
        if args.source
        else "Private source not supplied; acceptance pending"
    )


if __name__ == "__main__":
    main()
