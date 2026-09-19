from collections.abc import Iterator, MutableMapping
from typing import Any


class ReportStore(MutableMapping[str, dict[str, Any]]):
    """Small storage boundary for the prototype; replace internals with a database later."""

    def __init__(self) -> None:
        self._reports: dict[str, dict[str, Any]] = {}

    def create(self, report: dict[str, Any]) -> dict[str, Any]:
        report_id = report["id"]
        if report_id in self._reports:
            raise ValueError(f"Report already exists: {report_id}")
        self._reports[report_id] = report
        return report

    def get(self, report_id: str) -> dict[str, Any] | None:
        return self._reports.get(report_id)

    def __getitem__(self, report_id: str) -> dict[str, Any]:
        return self._reports[report_id]

    def __setitem__(self, report_id: str, report: dict[str, Any]) -> None:
        self._reports[report_id] = report

    def __delitem__(self, report_id: str) -> None:
        del self._reports[report_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self._reports)

    def __len__(self) -> int:
        return len(self._reports)

    def values(self):
        return self._reports.values()

    def delete_patient(self, patient_id: str) -> int:
        report_ids = [
            report_id
            for report_id, report in self._reports.items()
            if report.get("patient_id") == patient_id
        ]
        for report_id in report_ids:
            del self._reports[report_id]
        return len(report_ids)
