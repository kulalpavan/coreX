import json
import sqlite3
from collections.abc import Iterator, MutableMapping
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "storage" / "reports.sqlite3"
DEFAULT_FILE_DIRECTORY = Path(__file__).resolve().parent.parent / "storage" / "uploads"


class ReportStore(MutableMapping[str, dict[str, Any]]):
    """SQLite-backed report store with user management and ownership support."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_directory = self.database_path.parent / "uploads"
        self.file_directory.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        
        # Initialize users table
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        
        # Initialize reports table
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT '',
                patient_id TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        
        # Check if user_id column exists on reports table (migration safety)
        table_info = self._connection.execute("PRAGMA table_info(reports)").fetchall()
        column_names = {row["name"] for row in table_info}
        if "user_id" not in column_names:
            self._connection.execute("ALTER TABLE reports ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
            
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id)")
        
        self._connection.commit()
        rows = self._connection.execute("SELECT id, payload FROM reports").fetchall()
        self._reports = {row["id"]: json.loads(row["payload"]) for row in rows}

    # --- User Storage Methods ---
    def create_user(self, user_id: str, email: str, password_hash: str) -> dict[str, Any]:
        email_normalized = email.strip().lower()
        existing = self.get_user_by_email(email_normalized)
        if existing:
            raise ValueError("An account with this email already exists.")
        now = datetime.now().isoformat(timespec="seconds")
        self._connection.execute(
            "INSERT INTO users (id, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email_normalized, password_hash, now, now),
        )
        self._connection.commit()
        return {"id": user_id, "email": email_normalized, "created_at": now, "updated_at": now}

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        email_normalized = email.strip().lower()
        row = self._connection.execute("SELECT * FROM users WHERE email = ?", (email_normalized,)).fetchone()
        if not row:
            return None
        return dict(row)

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        row = self._connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return dict(row)

    # --- Report Persist Methods ---
    def _persist(self, report: dict[str, Any]) -> None:
        self._connection.execute(
            """
            INSERT INTO reports (id, user_id, patient_id, status, payload) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET user_id=excluded.user_id, patient_id=excluded.patient_id, status=excluded.status, payload=excluded.payload
            """,
            (
                report["id"],
                report.get("user_id", ""),
                report.get("patient_id", ""),
                report.get("status", "pending_review"),
                json.dumps(report),
            ),
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

    def get_for_user(self, report_id: str, user_id: str) -> dict[str, Any] | None:
        report = self._reports.get(report_id)
        if not report or report.get("user_id") != user_id:
            return None
        return report

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        user_reports = [r for r in self._reports.values() if r.get("user_id") == user_id]
        user_reports.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return user_reports

    def delete_for_user(self, report_id: str, user_id: str) -> bool:
        report = self.get_for_user(report_id, user_id)
        if not report:
            return False
        del self[report_id]
        return True

    def __getitem__(self, report_id: str) -> dict[str, Any]:
        return self._reports[report_id]

    def __setitem__(self, report_id: str, report: dict[str, Any]) -> None:
        report["id"] = report_id
        self._reports[report_id] = report
        self._persist(report)

    def __delitem__(self, report_id: str) -> None:
        report = self._reports[report_id]
        del self._reports[report_id]
        self._connection.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        self._connection.commit()
        raw_file_path = report.get("raw_file_path")
        if raw_file_path:
            Path(raw_file_path).unlink(missing_ok=True)

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
        self._connection.execute("DELETE FROM users")
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

