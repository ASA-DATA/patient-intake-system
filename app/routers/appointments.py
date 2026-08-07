from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.appointment import AvailabilityResponse
from app.services.availability import get_available_slots
from uuid import UUID

from app.schemas.appointment import (
    RescheduleAppointmentRequest,
    RescheduleAppointmentResponse,
)
from app.services.appointment_service import (
    reschedule_appointment,
)

router = APIRouter(
    prefix="/api/appointments",
    tags=["Appointments"],
)


@router.get(
    "/availability",
    response_model=AvailabilityResponse,
)
async def availability(
    db: AsyncSession = Depends(get_db),
) -> AvailabilityResponse:
    slots = await get_available_slots(db)

    return AvailabilityResponse(
        timezone=settings.clinic_timezone,
        slots=slots,
    )

@router.patch(
    "/{appointment_id}/reschedule",
    response_model=RescheduleAppointmentResponse,
)
async def reschedule(
    appointment_id: UUID,
    payload: RescheduleAppointmentRequest,
    db: AsyncSession = Depends(get_db),
) -> RescheduleAppointmentResponse:
    return await reschedule_appointment(
        db=db,
        appointment_id=appointment_id,
        new_starts_at=payload.starts_at,
    )