from __future__ import annotations

import argparse
import json
import mimetypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .extraction import ExtractionError, extract_candidates, process_report

FIELDS = ("test_name", "value", "unit", "reference_range", "report_date")


@dataclass
class FieldMetric:
    field: str
    expected: int
    extracted: int
    matched: int
    precision: float
    recall: float


@dataclass
class Failure:
    report_id: str
    stage: str
    field: str
    message: str


def _precision(matched: int, extracted: int) -> float:
    return round(matched / extracted, 3) if extracted else 0.0


def _recall(matched: int, expected: int) -> float:
    return round(matched / expected, 3) if expected else 1.0


def _same_number(left: Any, right: Any, tolerance: float = 0.01) -> bool:
    if left is None or right is None:
        return left is right
    return abs(float(left) - float(right)) <= tolerance


def _same_range(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    return _same_number(expected.get("low"), actual.get("reference_range_low")) and _same_number(expected.get("high"), actual.get("reference_range_high"))


def evaluate_report(report_id: str, expected: dict[str, Any], actual: list[dict[str, Any]]) -> tuple[list[FieldMetric], list[Failure]]:
    failures: list[Failure] = []
    expected_tests = expected.get("tests", [])
    actual_by_name = {item.get("raw_test_name", "").casefold(): item for item in actual}
    fields: list[FieldMetric] = []
    for field in FIELDS:
        expected_count = len(expected_tests) if field != "report_date" else int(bool(expected.get("report_date")))
        matched = 0
        extracted_count = len(actual) if field != "report_date" else int(bool(actual and actual[0].get("report_date")))
        if field == "report_date":
            if expected.get("report_date") and actual and actual[0].get("report_date") == expected["report_date"]:
                matched = 1
            elif expected.get("report_date"):
                failures.append(Failure(report_id, "date_extraction", field, "Report date did not match ground truth."))
        else:
            for expected_test in expected_tests:
                actual_test = actual_by_name.get(expected_test["test_name"].casefold())
                if actual_test is None:
                    failures.append(Failure(report_id, "test_name_matching", field, f"Missing test row: {expected_test['test_name']}"))
                    continue
                if field == "test_name":
                    matched += 1
                elif field == "value" and _same_number(expected_test.get("value"), actual_test.get("value")):
                    matched += 1
                elif field == "unit" and expected_test.get("unit") == actual_test.get("unit"):
                    matched += 1
                elif field == "reference_range" and _same_range(expected_test.get("reference_range", {}), actual_test):
                    matched += 1
                else:
                    failures.append(Failure(report_id, f"{field}_parsing", field, f"Value mismatch for {expected_test['test_name']}"))
        fields.append(FieldMetric(field, expected_count, extracted_count, matched, _precision(matched, extracted_count), _recall(matched, expected_count)))
    return fields, failures


def evaluate_text_fixtures(fixture_dir: Path, ground_truth_path: Path) -> dict[str, Any]:
    ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    reports = ground_truth.get("reports", [])
    metrics: list[FieldMetric] = []
    failures: list[Failure] = []
    for report in reports:
        report_id = report["report_id"]
        source = fixture_dir / report["source_file"]
        try:
            if source.suffix.lower() == ".txt":
                actual = extract_candidates(source.read_text(encoding="utf-8"))
            else:
                content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
                actual = process_report(source.read_bytes(), content_type, source.name)["results"]
        except ExtractionError as error:
            failures.append(Failure(report_id, "text_normalization", "test_name", str(error)))
            actual = []
        report_metrics, report_failures = evaluate_report(report_id, report, actual)
        metrics.extend(report_metrics)
        failures.extend(report_failures)
    return {"metrics": [asdict(metric) for metric in metrics], "failures": [asdict(failure) for failure in failures]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate field-level extraction against local ground truth.")
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate_text_fixtures(args.fixture_dir, args.ground_truth), indent=2))


if __name__ == "__main__":
    main()
