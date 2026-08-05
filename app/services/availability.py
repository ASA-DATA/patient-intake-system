from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import AvailableSlot

from fastapi import HTTPException, status

async def get_available_slots(
    db: AsyncSession,
) -> list[AvailableSlot]:
    clinic_timezone = ZoneInfo(settings.clinic_timezone)
    now = datetime.now(clinic_timezone)

    start_date = now.date()
    end_date = start_date + timedelta(
        days=settings.availability_days
    )

    range_start = datetime.combine(
        start_date,
        time.min,
        tzinfo=clinic_timezone,
    )

    range_end = datetime.combine(
        end_date,
        time.max,
        tzinfo=clinic_timezone,
    )

    statement = select(Appointment.starts_at).where(
        Appointment.starts_at >= range_start,
        Appointment.starts_at <= range_end,
        Appointment.status.in_(
            [
                AppointmentStatus.pending,
                AppointmentStatus.confirmed,
            ]
        ),
    )

    result = await db.execute(statement)

    occupied_slots = {
        starts_at.astimezone(clinic_timezone)
        for starts_at in result.scalars().all()
    }

    available_slots: list[AvailableSlot] = []

    duration = timedelta(
        minutes=settings.appointment_duration_minutes
    )

    for day_offset in range(settings.availability_days + 1):
        current_date = start_date + timedelta(days=day_offset)

        if current_date.weekday() >= 5:
            continue

        current_start = datetime.combine(
            current_date,
            time(hour=settings.opening_hour),
            tzinfo=clinic_timezone,
        )

        closing_datetime = datetime.combine(
            current_date,
            time(hour=settings.closing_hour),
            tzinfo=clinic_timezone,
        )

        while current_start + duration <= closing_datetime:
            current_end = current_start + duration

            if current_start > now and current_start not in occupied_slots:
                available_slots.append(
                    AvailableSlot(
                        starts_at=current_start,
                        ends_at=current_end,
                        label=current_start.strftime(
                            "%d/%m/%Y %I:%M %p"
                        ),
                    )
                )

            current_start += duration

    return available_slots

from fastapi import HTTPException, status
def validate_requested_slot(
    starts_at: datetime,
) -> tuple[datetime, datetime]:
    clinic_timezone = ZoneInfo(settings.clinic_timezone)

    local_start = starts_at.astimezone(clinic_timezone)
    now = datetime.now(clinic_timezone)

    if local_start <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El horario solicitado ya pasó.",
        )

    if local_start.weekday() >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las citas solo están disponibles de lunes a viernes.",
        )

    if local_start.minute != 0 or local_start.second != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cita debe comenzar en una hora exacta.",
        )

    duration = timedelta(
        minutes=settings.appointment_duration_minutes
    )

    local_end = local_start + duration

    opening_datetime = datetime.combine(
        local_start.date(),
        time(hour=settings.opening_hour),
        tzinfo=clinic_timezone,
    )

    closing_datetime = datetime.combine(
        local_start.date(),
        time(hour=settings.closing_hour),
        tzinfo=clinic_timezone,
    )

    if (
        local_start < opening_datetime
        or local_end > closing_datetime
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "El horario está fuera del horario de atención."
            ),
        )

    maximum_date = now.date() + timedelta(
        days=settings.availability_days
    )

    if local_start.date() > maximum_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La cita está fuera del periodo disponible."
            ),
        )

    return local_start, local_end