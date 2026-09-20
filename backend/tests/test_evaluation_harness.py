from pathlib import Path

from app.evaluation import evaluate_text_fixtures


ROOT = Path(__file__).parent


def test_evaluation_harness_reports_field_metrics_and_failures() -> None:
    result = evaluate_text_fixtures(ROOT / "fixtures", ROOT / "fixtures" / "ground_truth.json")

    metrics = {metric["field"]: metric for metric in result["metrics"]}
    assert metrics["test_name"]["precision"] >= 0.8
    assert metrics["test_name"]["recall"] >= 0.8
    assert metrics["value"]["precision"] == 1.0
    assert metrics["reference_range"]["recall"] >= 0.8
    assert isinstance(result["failures"], list)
