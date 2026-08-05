from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import AvailableSlot


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