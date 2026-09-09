from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.schemas.appointment import (
    AvailabilityResponse,
    CancelAppointmentResponse,
    RescheduleAppointmentRequest,
    RescheduleAppointmentResponse,
)
from app.schemas.records import (
    AppointmentListItem,
    PaginatedAppointmentsResponse,
)
from app.services.appointment_service import (
    cancel_appointment,
    reschedule_appointment,
)
from app.services.availability import get_available_slots
from app.services.date_ranges import clinic_date_bounds

router = APIRouter(
    prefix="/api/appointments",
    tags=["Appointments"],
)
# Approved endpoint
@router.get(
    "/by-date",
    response_model=PaginatedAppointmentsResponse,
)
async def get_appointments_by_date(
    start_date: date,
    end_date: date,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedAppointmentsResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date no puede ser mayor que end_date",
        )

    start_datetime, end_datetime = clinic_date_bounds(start_date, end_date)
    filters = (
        Appointment.starts_at >= start_datetime,
        Appointment.starts_at < end_datetime,
    )

    total_query = (
        select(func.count())
        .select_from(Appointment)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(*filters)
    )
    total = (await db.execute(total_query)).scalar_one()

    appointments_query = (
        select(
            Appointment.id.label("appointment_id"),
            Appointment.intake_submission_id,
            Patient.id.label("patient_id"),
            Patient.full_name.label("patient_name"),
            Patient.phone,
            Appointment.starts_at,
            Appointment.ends_at,
            Appointment.status,
        )
        .select_from(Appointment)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(*filters)
        .order_by(Appointment.starts_at, Appointment.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(appointments_query)).mappings().all()

    return PaginatedAppointmentsResponse(
        items=[AppointmentListItem(**row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
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

@router.patch(
    "/{appointment_id}/cancel",
    response_model=CancelAppointmentResponse,
)
async def cancel(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CancelAppointmentResponse:
    return await cancel_appointment(
        db=db,
        appointment_id=appointment_id,
    )
