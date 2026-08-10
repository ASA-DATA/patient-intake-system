import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.google_calendar import (
    create_calendar_event,
)
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.integrations.google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    update_calendar_event,
)

logger = logging.getLogger(__name__)


async def sync_new_appointment_to_calendar(
    db: AsyncSession,
    appointment: Appointment,
    patient: Patient,
) -> None:
    try:
        result = create_calendar_event(
            summary=f"Cita - {patient.full_name}",
            description=(
                f"Paciente: {patient.full_name}\n"
                f"Teléfono: {patient.phone}"
            ),
            starts_at=appointment.starts_at,
            ends_at=appointment.ends_at,
        )

        appointment.google_calendar_event_id = (
            result["event_id"]
        )
        appointment.google_calendar_event_link = (
            result["html_link"]
        )
        appointment.google_calendar_sync_status = "synced"

    except Exception:
        logger.exception(
            "No fue posible crear el evento de Google Calendar "
            "para la cita %s.",
            appointment.id,
        )

        appointment.google_calendar_sync_status = "failed"

    db.add(appointment)

    try:
        await db.commit()
        await db.refresh(appointment)

    except Exception:
        await db.rollback()

        logger.exception(
            "No fue posible guardar los metadatos de Calendar "
            "para la cita %s.",
            appointment.id,
        )

async def sync_rescheduled_appointment_to_calendar(
    db: AsyncSession,
    appointment: Appointment,
) -> None:
    event_id = appointment.google_calendar_event_id

    if not event_id:
        logger.warning(
            "La cita %s no tiene event_id de Google Calendar.",
            appointment.id,
        )

        appointment.google_calendar_sync_status = "failed"

        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        return

    try:
        result = update_calendar_event(
            event_id=event_id,
            starts_at=appointment.starts_at,
            ends_at=appointment.ends_at,
        )

        appointment.google_calendar_event_link = (
            result["html_link"]
        )

        appointment.google_calendar_sync_status = "synced"

    except Exception:
        logger.exception(
            "No fue posible actualizar Google Calendar "
            "para la cita %s.",
            appointment.id,
        )

        appointment.google_calendar_sync_status = "failed"

    db.add(appointment)

    try:
        await db.commit()
        await db.refresh(appointment)

    except Exception:
        await db.rollback()

        logger.exception(
            "No fue posible guardar el estado de "
            "sincronización de Calendar para la cita %s.",
            appointment.id,
        )

async def sync_cancelled_appointment_to_calendar(
    db: AsyncSession,
    appointment: Appointment,
) -> None:
    event_id = appointment.google_calendar_event_id

    if not event_id:
        logger.error(
            "La cita %s no tiene google_calendar_event_id.",
            appointment.id,
        )

        appointment.google_calendar_sync_status = "failed"

        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        return

    try:
        print(
            f"Eliminando evento Calendar: {event_id}"
        )

        delete_calendar_event(
            event_id=event_id,
        )

        print(
            f"Evento Calendar eliminado: {event_id}"
        )

        appointment.google_calendar_sync_status = "deleted"

    except Exception as exc:
        logger.exception(
            "Error eliminando Google Calendar "
            "para cita %s. Event ID: %s",
            appointment.id,
            event_id,
        )

        print(
            "ERROR GOOGLE CALENDAR:",
            repr(exc),
        )

        appointment.google_calendar_sync_status = "failed"

    db.add(appointment)

    try:
        await db.commit()
        await db.refresh(appointment)

    except Exception:
        await db.rollback()

        logger.exception(
            "No fue posible guardar el estado de Calendar "
            "para la cita %s.",
            appointment.id,
        )