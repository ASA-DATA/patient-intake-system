from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.appointment import AvailabilityResponse
from app.services.availability import get_available_slots


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