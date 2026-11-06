# app/test_summary_parser.py
from pathlib import Path
import xml.etree.ElementTree as ET


def parse_junit_counts(xml_path):
    """
    Return {'total': n, 'passed': n, 'failed': n, 'skipped': n}
    from a pytest JUnit XML file.
    """
    xml_path = Path(xml_path)
    if not xml_path.is_file():
        return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

    root = ET.parse(xml_path).getroot()

    total = int(root.get("tests", 0) or 0)
    failures = int(root.get("failures", 0) or 0)
    errors = int(root.get("errors", 0) or 0)
    skipped = int(root.get("skipped", 0) or 0)

    failed = failures + errors
    passed = max(total - failed - skipped, 0)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }