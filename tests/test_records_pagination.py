import unittest
from datetime import date
from uuid import uuid4

from fastapi import HTTPException

from app.main import app
from app.routers.records import get_record_detail, get_records
from app.schemas.records import (
    AppointmentListItem,
    RecordListItem,
    RecordPatientDetail,
    RecordSubmissionDetail,
)


class _ScalarResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _MappingResult:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self) -> "_MappingResult":
        return self

    def all(self) -> list[dict]:
        return self.rows

    def one_or_none(self) -> dict | None:
        return self.rows[0] if self.rows else None


class _FakeSession:
    def __init__(self, results: list[object]) -> None:
        self.results = results
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return self.results.pop(0)


class RecordsPaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_total_pages_rounds_up(self) -> None:
        session = _FakeSession([_ScalarResult(51), _MappingResult([])])

        response = await get_records(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            page=2,
            page_size=25,
            db=session,
        )

        self.assertEqual(response.total_pages, 3)
        self.assertEqual(response.total, 51)
        self.assertEqual(len(session.statements), 2)

    async def test_missing_record_returns_404(self) -> None:
        session = _FakeSession([_MappingResult([])])

        with self.assertRaises(HTTPException) as raised:
            await get_record_detail(uuid4(), session)

        self.assertEqual(raised.exception.status_code, 404)

    def test_page_size_is_limited_to_100(self) -> None:
        openapi = app.openapi()

        for path in ("/api/records", "/api/appointments/by-date"):
            parameters = openapi["paths"][path]["get"]["parameters"]
            page_size = next(
                parameter
                for parameter in parameters
                if parameter["name"] == "page_size"
            )
            self.assertEqual(page_size["schema"]["maximum"], 100)

    def test_public_schemas_exclude_internal_columns(self) -> None:
        self.assertEqual(
            set(RecordListItem.model_fields),
            {
                "submission_id",
                "patient_id",
                "full_name",
                "age",
                "sex",
                "occupation",
                "assessment_date",
                "alarm_flag",
            },
        )
        self.assertEqual(
            set(RecordPatientDetail.model_fields),
            {
                "patient_id",
                "full_name",
                "age",
                "sex",
                "occupation",
                "phone",
            },
        )
        self.assertEqual(
            set(RecordSubmissionDetail.model_fields),
            {
                "submission_id",
                "patient_id",
                "assessment_date",
                "answers",
                "alarm_flag",
            },
        )
        self.assertEqual(
            set(AppointmentListItem.model_fields),
            {
                "appointment_id",
                "intake_submission_id",
                "patient_id",
                "patient_name",
                "phone",
                "starts_at",
                "ends_at",
                "status",
            },
        )


if __name__ == "__main__":
    unittest.main()
