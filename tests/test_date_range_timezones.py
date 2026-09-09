import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import operators

from app.core.config import settings
from app.core.database import get_db
from app.routers.appointments import router as appointments_router
from app.routers.records import router as records_router


class DateRangeTimezoneTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = AsyncMock(spec=AsyncSession)
        self.app = FastAPI()
        self.app.include_router(records_router)
        self.app.include_router(appointments_router)

        async def override_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_db

    async def request(self, path, start, end):
        async with AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test") as client:
            return await client.get(path, params={"start_date": start, "end_date": end})

    def assert_bounds(self, statement, expected_start, expected_end):
        lower, upper = list(statement.whereclause.clauses)
        self.assertIs(lower.operator, operators.ge)
        self.assertIs(upper.operator, operators.lt)
        self.assertTrue(lower.left.type.timezone)
        self.assertTrue(upper.left.type.timezone)
        values = [v for v in statement.compile().params.values() if isinstance(v, datetime)]
        self.assertEqual(len(values), 2)
        for value in values:
            self.assertIsNotNone(value.tzinfo)
            self.assertIsNotNone(value.utcoffset())
        lower_utc, upper_utc = [v.astimezone(timezone.utc) for v in values]
        self.assertEqual(lower_utc, datetime.fromisoformat(expected_start))
        self.assertEqual(upper_utc, datetime.fromisoformat(expected_end))

        # The SQL predicates must include midnight and the last microsecond,
        # but exclude adjacent clinic days, even when UTC is another date.
        for instant, expected in (
            (lower_utc - timedelta(microseconds=1), False),
            (lower_utc, True),
            (upper_utc - timedelta(microseconds=1), True),
            (upper_utc, False),
        ):
            self.assertEqual(lower.operator(instant, lower_utc) and upper.operator(instant, upper_utc), expected)

    async def test_appointments_count_and_rows_use_same_clinic_day(self):
        cases = (
            ("America/Mexico_City", "2026-01-01", "2026-01-01T06:00:00+00:00", "2026-01-02T06:00:00+00:00"),
            ("Asia/Tokyo", "2026-01-01", "2025-12-31T15:00:00+00:00", "2026-01-01T15:00:00+00:00"),
            ("America/New_York", "2026-03-08", "2026-03-08T05:00:00+00:00", "2026-03-09T04:00:00+00:00"),
            ("America/New_York", "2026-11-01", "2026-11-01T04:00:00+00:00", "2026-11-02T05:00:00+00:00"),
        )
        for zone, day, lower, upper in cases:
            with self.subTest(zone=zone, day=day), patch.object(settings, "clinic_timezone", zone):
                self.db.reset_mock()
                rows = Mock()
                rows.mappings.return_value.all.return_value = []
                self.db.execute.side_effect = [Mock(scalar_one=Mock(return_value=0)), rows]
                response = await self.request("/api/appointments/by-date", day, day)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["total"], 0)
                self.assertEqual(self.db.execute.await_count, 2)
                for call in self.db.execute.call_args_list:
                    self.assert_bounds(call.args[0], lower, upper)

    async def test_legacy_records_uses_aware_bounds_and_preserves_lookback(self):
        rows = Mock()
        rows.scalars.return_value.all.return_value = []
        self.db.execute.side_effect = [rows, rows, rows]
        with patch.object(settings, "clinic_timezone", "America/New_York"):
            response = await self.request("/api/records/by-date", "2026-03-08", "2026-03-08")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["appointments"], [])
        self.assertEqual(self.db.execute.await_count, 3)
        for call in self.db.execute.call_args_list[:2]:
            self.assert_bounds(call.args[0], "2026-02-26T05:00:00+00:00", "2026-03-09T04:00:00+00:00")
        self.assert_bounds(self.db.execute.call_args_list[2].args[0], "2026-03-08T05:00:00+00:00", "2026-03-09T04:00:00+00:00")

    async def test_invalid_ranges_rejected_before_database_access(self):
        for path in ("/api/records", "/api/records/by-date", "/api/appointments/by-date"):
            with self.subTest(path=path):
                response = await self.request(path, "2026-01-02", "2026-01-01")
                self.assertEqual(response.status_code, 400)
                self.db.execute.assert_not_called()

    async def test_assessment_date_remains_a_date_filter(self):
        rows = Mock()
        rows.mappings.return_value.all.return_value = []
        self.db.execute.side_effect = [Mock(scalar_one=Mock(return_value=0)), rows]
        response = await self.request("/api/records", "2026-01-01", "2026-01-02")
        self.assertEqual(response.status_code, 200)
        for call in self.db.execute.call_args_list:
            filters = list(call.args[0].whereclause.clauses)
            self.assertEqual([f.right.value for f in filters], [date(2026, 1, 1), date(2026, 1, 2)])
            self.assertTrue(all(type(f.right.value) is date for f in filters))
            self.assertIs(filters[1].operator, operators.le)
