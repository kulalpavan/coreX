from pathlib import Path

from app.storage import ReportStore


def test_report_store_reloads_confirmed_report_from_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "reports.sqlite3"
    first_store = ReportStore(database_path)
    first_store.create(
        {
            "id": "report_1",
            "patient_id": "p_demo",
            "status": "pending_review",
            "results": [],
            "raw_text": "Hemoglobin 13.8 g/dL",
        }
    )
    report = first_store["report_1"]
    report["status"] = "confirmed"
    first_store.save(report)
    first_store.close()

    second_store = ReportStore(database_path)

    assert second_store["report_1"]["status"] == "confirmed"
    assert second_store["report_1"]["raw_text"] == "Hemoglobin 13.8 g/dL"
    second_store.close()
