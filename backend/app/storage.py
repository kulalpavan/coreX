import json
import sqlite3
from collections.abc import Iterator, MutableMapping
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "storage" / "reports.sqlite3"


class ReportStore(MutableMapping[str, dict[str, Any]]):
    """SQLite-backed report store with the existing mapping interface."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        self._connection.commit()
        rows = self._connection.execute("SELECT id, payload FROM reports").fetchall()
        self._reports = {row["id"]: json.loads(row["payload"]) for row in rows}

    def _persist(self, report: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO reports (id, patient_id, status, payload) VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET patient_id=excluded.patient_id, status=excluded.status, payload=excluded.payload
            """,
            (report["id"], report.get("patient_id", ""), report.get("status", "pending_review"), json.dumps(report)),
        )
        self._connection.commit()

    def create(self, report: dict[str, Any]) -> dict[str, Any]:
        if report["id"] in self._reports:
            raise ValueError(f"Report already exists: {report['id']}")
        self._reports[report["id"]] = report
        self._persist(report)
        return report

    def save(self, report: dict[str, Any]) -> dict[str, Any]:
        if report["id"] not in self._reports:
            raise KeyError(report["id"])
        self._reports[report["id"]] = report
        self._persist(report)
        return report

    def get(self, report_id: str) -> dict[str, Any] | None:
        return self._reports.get(report_id)

    def __getitem__(self, report_id: str) -> dict[str, Any]:
        return self._reports[report_id]

    def __setitem__(self, report_id: str, report: dict[str, Any]) -> None:
        report["id"] = report_id
        self._reports[report_id] = report
        self._persist(report)

    def __delitem__(self, report_id: str) -> None:
        del self._reports[report_id]
        self._connection.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        self._connection.commit()

    def __iter__(self) -> Iterator[str]:
        return iter(self._reports)

    def __len__(self) -> int:
        return len(self._reports)

    def values(self):
        return self._reports.values()

    def delete_patient(self, patient_id: str) -> int:
        report_ids = [report_id for report_id, report in self._reports.items() if report.get("patient_id") == patient_id]
        for report_id in report_ids:
            del self[report_id]
        return len(report_ids)

    def clear(self) -> None:
        self._reports.clear()
        self._connection.execute("DELETE FROM reports")
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()
