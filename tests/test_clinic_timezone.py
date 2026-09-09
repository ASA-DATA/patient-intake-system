import unittest
from datetime import datetime
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.integrations import google_calendar
from app.main import app


class CalendarTimezoneTests(unittest.TestCase):
    def test_create_and_update_preserve_instant_in_configured_timezone(self):
        cases = (
            ("America/Mexico_City", "2026-01-01T01:30:00+00:00", "2025-12-31T19:30:00-06:00"),
            ("Asia/Tokyo", "2026-01-01T01:30:00+00:00", "2026-01-01T10:30:00+09:00"),
            ("America/New_York", "2026-03-08T06:30:00+00:00", "2026-03-08T01:30:00-05:00"),
            ("America/New_York", "2026-03-08T07:30:00+00:00", "2026-03-08T03:30:00-04:00"),
            ("America/New_York", "2026-11-01T06:30:00+00:00", "2026-11-01T01:30:00-05:00"),
        )
        for operation in ("create", "update"):
            for zone, instant, expected in cases:
                with self.subTest(operation=operation, zone=zone, instant=instant):
                    with patch.object(settings, "clinic_timezone", zone), patch.object(
                        google_calendar, "get_calendar_service"
                    ) as get_service:
                        events = get_service.return_value.events.return_value
                        events.get.return_value.execute.return_value = {"summary": "Conservar título"}
                        request = events.insert if operation == "create" else events.update
                        request.return_value.execute.return_value = {"id": "test-event"}
                        value = datetime.fromisoformat(instant)
                        if operation == "create":
                            response = google_calendar.create_calendar_event("Prueba", "Detalle", value, value)
                        else:
                            response = google_calendar.update_calendar_event("test-event", value, value)
                        self.assertEqual(response["event_id"], "test-event")
                        body = request.call_args.kwargs["body"]
                        for boundary in ("start", "end"):
                            self.assertEqual(body[boundary], {"dateTime": expected, "timeZone": zone})
                            self.assertEqual(datetime.fromisoformat(body[boundary]["dateTime"]), value)
                        if operation == "update":
                            self.assertEqual(body["summary"], "Conservar título")

    def test_naive_input_is_rejected_before_google_access(self):
        aware = datetime.fromisoformat("2026-01-01T12:00:00+00:00")
        naive = aware.replace(tzinfo=None)
        for start, end in ((naive, aware), (aware, naive)):
            for operation in ("create", "update"):
                with self.subTest(operation=operation, start=start, end=end):
                    with patch.object(google_calendar, "get_calendar_service") as get_service:
                        with self.assertRaisesRegex(ValueError, "debe incluir zona horaria"):
                            if operation == "create":
                                google_calendar.create_calendar_event("Prueba", "Detalle", start, end)
                            else:
                                google_calendar.update_calendar_event("test-event", start, end)
                        get_service.assert_not_called()

    def test_settings_reject_invalid_timezone(self):
        for zone in ("Invalid/Clinic", "", "/etc/localtime"):
            with self.subTest(zone=zone), self.assertRaises(ValidationError):
                Settings(_env_file=None, database_url="postgresql+asyncpg://test:test@localhost/test", clinic_timezone=zone)


class PublicTimezoneTests(unittest.IsolatedAsyncioTestCase):
    async def test_endpoint_exposes_only_configured_timezone(self):
        with patch.object(settings, "clinic_timezone", "Asia/Tokyo"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"clinic_timezone": "Asia/Tokyo"})
