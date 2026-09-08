import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.routers.appointments import router
from app.services import appointment_service


class AppointmentStatusValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.start = datetime(2030, 1, 7, 15, tzinfo=timezone.utc)
        self.new_start = self.start + timedelta(days=1)
        self.new_end = self.new_start + timedelta(hours=1)
        self.db = AsyncMock(spec=AsyncSession)
        self.effects = {}
        for name in (
            "sync_rescheduled_appointment_to_calendar",
            "sync_cancelled_appointment_to_calendar",
            "notify_clinic_rescheduled_appointment",
            "notify_patient_rescheduled_appointment",
            "notify_clinic_cancelled_appointment",
            "notify_patient_cancelled_appointment",
            "validate_requested_slot",
        ):
            patcher = patch.object(appointment_service, name)
            self.effects[name] = patcher.start()
            self.addCleanup(patcher.stop)
        self.effects["validate_requested_slot"].return_value = (
            self.new_start, self.new_end
        )
        self.app = FastAPI()
        self.app.include_router(router)

        async def override_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_db

    def prepare(self, status):
        self.db.reset_mock()
        for effect in self.effects.values():
            effect.reset_mock()
        appointment = Appointment(
            id=uuid4(), patient_id=uuid4(), intake_submission_id=uuid4(),
            status=status, starts_at=self.start,
            ends_at=self.start + timedelta(hours=1),
            google_calendar_event_id="existing-event",
            google_calendar_sync_status="synced",
        )
        self.patient = SimpleNamespace(id=appointment.patient_id)
        self.submission = SimpleNamespace(whatsapp_consent=True)
        self.db.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=appointment)),
            Mock(scalar_one=Mock(return_value=self.patient)),
            Mock(scalar_one=Mock(return_value=self.submission)),
            Mock(scalar_one_or_none=Mock(return_value=None)),
        ]
        return appointment

    async def request(self, action, appointment):
        async with AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://test"
        ) as client:
            return await client.patch(
                f"/api/appointments/{appointment.id}/{action}",
                **({"json": {"starts_at": self.new_start.isoformat()}}
                   if action == "reschedule" else {}),
            )

    async def assert_rejected(self, action, messages):
        for status, message in messages.items():
            with self.subTest(action=action, status=status):
                appointment = self.prepare(status)
                before = dict(vars(appointment))
                response = await self.request(action, appointment)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json(), {"detail": message})
                self.assertEqual(vars(appointment), before)
                self.db.execute.assert_awaited_once()
                self.db.commit.assert_not_called()
                self.db.flush.assert_not_called()
                self.db.add.assert_not_called()
                self.db.delete.assert_not_called()
                self.db.refresh.assert_not_called()
                for effect in self.effects.values():
                    effect.assert_not_called()

    async def test_reschedule_rejects_inactive_without_side_effects(self):
        await self.assert_rejected("reschedule", {
            AppointmentStatus.completed: "No se puede reagendar una cita finalizada.",
            AppointmentStatus.cancelled: "No se puede reagendar una cita cancelada.",
        })

    async def test_cancel_rejects_inactive_without_side_effects(self):
        await self.assert_rejected("cancel", {
            AppointmentStatus.completed: "No se puede cancelar una cita finalizada.",
            AppointmentStatus.cancelled: "La cita ya está cancelada.",
        })

    async def assert_active(self, action):
        for status in (AppointmentStatus.pending, AppointmentStatus.confirmed):
            with self.subTest(action=action, status=status):
                appointment = self.prepare(status)
                response = await self.request(action, appointment)
                self.assertEqual(response.status_code, 200, response.text)
                expected = (AppointmentStatus.confirmed if action == "reschedule"
                            else AppointmentStatus.cancelled)
                self.assertEqual(appointment.status, expected)
                self.assertEqual(response.json()["status"], expected.value)
                self.assertEqual(response.json()["appointment_id"], str(appointment.id))
                self.db.commit.assert_awaited_once()
                self.db.refresh.assert_awaited_once_with(appointment)
                self.db.rollback.assert_not_called()
                if action == "reschedule":
                    self.assertEqual(appointment.starts_at, self.new_start)
                    self.assertEqual(appointment.ends_at, self.new_end)
                    self.effects["validate_requested_slot"].assert_called_once_with(self.new_start)
                else:
                    self.assertEqual(appointment.starts_at, self.start)
                    self.assertEqual(appointment.ends_at, self.start + timedelta(hours=1))
                    self.effects["validate_requested_slot"].assert_not_called()
                suffix = "rescheduled" if action == "reschedule" else "cancelled"
                self.effects[f"sync_{suffix}_appointment_to_calendar"].assert_awaited_once_with(
                    db=self.db, appointment=appointment
                )
                self.effects[f"notify_clinic_{suffix}_appointment"].assert_called_once_with(
                    appointment=appointment, patient=self.patient
                )
                self.effects[f"notify_patient_{suffix}_appointment"].assert_called_once_with(
                    appointment=appointment, patient=self.patient, whatsapp_consent=True
                )
                other = "cancelled" if action == "reschedule" else "rescheduled"
                for name, effect in self.effects.items():
                    if other in name:
                        effect.assert_not_called()

    async def test_reschedule_allows_active(self):
        await self.assert_active("reschedule")

    async def test_cancel_allows_active(self):
        await self.assert_active("cancel")
