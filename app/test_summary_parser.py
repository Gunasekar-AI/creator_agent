from pathlib import Path
import xml.etree.ElementTree as ET


def _int(el, name):
    try:
        return int(el.get(name, 0) or 0)
    except (TypeError, ValueError):
        return 0


def parse_junit_counts(xml_path):
    xml_path = Path(xml_path)
    if not xml_path.is_file():
        return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

    root = ET.parse(xml_path).getroot()

    # pytest emits <testsuite ...> at the root; some tools wrap in <testsuites>.
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
        total = sum(_int(s, "tests") for s in suites)
        failures = sum(_int(s, "failures") for s in suites)
        errors = sum(_int(s, "errors") for s in suites)
        skipped = sum(_int(s, "skipped") for s in suites)
    else:
        total = _int(root, "tests")
        failures = _int(root, "failures")
        errors = _int(root, "errors")
        skipped = _int(root, "skipped")

    failed = failures + errors
    passed = max(total - failed - skipped, 0)
    return {"total": total, "passed": passed, "failed": failed, "skipped": skipped}