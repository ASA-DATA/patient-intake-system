from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import (
    Appointment,
    AppointmentStatus,
)
from app.schemas.appointment import (
    RescheduleAppointmentResponse,CancelAppointmentResponse,
)

from app.services.availability import (
    validate_requested_slot,
)
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import CancelAppointmentResponse
from app.services.calendar_service import (
    sync_cancelled_appointment_to_calendar,
    sync_rescheduled_appointment_to_calendar,
)

from app.models.patient import Patient
from app.models.intake import IntakeSubmission

from app.services.whatsapp_service import (
    notify_clinic_cancelled_appointment,
    notify_clinic_rescheduled_appointment,
    notify_patient_cancelled_appointment,
    notify_patient_rescheduled_appointment,
)

async def reschedule_appointment(
    db: AsyncSession,
    appointment_id: UUID,
    new_starts_at,
) -> RescheduleAppointmentResponse:
    statement = select(Appointment).where(
        Appointment.id == appointment_id
    )

    result = await db.execute(statement)
    appointment = result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada.",
        )

    if appointment.status not in (
        AppointmentStatus.pending,
        AppointmentStatus.confirmed,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede reagendar una cita finalizada.",
        )

    patient_result = await db.execute(
    select(Patient).where(
            Patient.id == appointment.patient_id
        )
    )

    patient = patient_result.scalar_one()


    submission_result = await db.execute(
        select(IntakeSubmission).where(
            IntakeSubmission.id
            == appointment.intake_submission_id
        )
    )

    submission = submission_result.scalar_one()


    local_start, local_end = validate_requested_slot(
        new_starts_at
    )

    occupied_statement = select(Appointment.id).where(
        Appointment.starts_at == local_start,
        Appointment.id != appointment.id,
        Appointment.status.in_(
            [
                AppointmentStatus.pending,
                AppointmentStatus.confirmed,
            ]
        ),
    )

    occupied_result = await db.execute(
        occupied_statement
    )

    if occupied_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nuevo horario ya está reservado.",
        )

    appointment.starts_at = local_start
    appointment.ends_at = local_end
    appointment.status = AppointmentStatus.confirmed

    try:
        await db.commit()
        await db.refresh(appointment)

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nuevo horario ya fue reservado.",
        ) from exc



    await sync_rescheduled_appointment_to_calendar(
    db=db,
    appointment=appointment,
)

    notify_clinic_rescheduled_appointment(
    appointment=appointment,
    patient=patient,
)

    notify_patient_rescheduled_appointment(
    appointment=appointment,
    patient=patient,
    whatsapp_consent=submission.whatsapp_consent,
)
    clinic_timezone = ZoneInfo(
    settings.clinic_timezone
)

    local_start = appointment.starts_at.astimezone(
    clinic_timezone
)

    local_end = appointment.ends_at.astimezone(
    clinic_timezone
)
    return RescheduleAppointmentResponse(
    appointment_id=str(appointment.id),
    status=appointment.status.value,
    starts_at=local_start,
    ends_at=local_end,
    message="Cita reagendada correctamente.",
)

#Approved function
async def cancel_appointment(
    db: AsyncSession,
    appointment_id: UUID,
) -> CancelAppointmentResponse:
    
    statement = select(Appointment).where(
        Appointment.id == appointment_id
    )

    result = await db.execute(statement)
    appointment = result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada.",
        )


    if appointment.status not in (
        AppointmentStatus.pending,
        AppointmentStatus.confirmed,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede cancelar una cita finalizada.",
        )

    # AQUÍ
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == appointment.patient_id
        )
    )

    patient = patient_result.scalar_one()

    submission_result = await db.execute(
        select(IntakeSubmission).where(
            IntakeSubmission.id
            == appointment.intake_submission_id
        )
    )

    submission = submission_result.scalar_one()

    appointment.status = AppointmentStatus.cancelled




    try:
        await db.commit()
        await db.refresh(appointment)

    except Exception as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible cancelar la cita.",
        ) from exc


    await sync_cancelled_appointment_to_calendar(
    db=db,
    appointment=appointment,
)

    notify_clinic_cancelled_appointment(
    appointment=appointment,
    patient=patient,)

    notify_patient_cancelled_appointment(
    appointment=appointment,
    patient=patient,
    whatsapp_consent=submission.whatsapp_consent,)
    
    clinic_timezone = ZoneInfo(
        settings.clinic_timezone
    )

    local_start = appointment.starts_at.astimezone(
        clinic_timezone
    )

    local_end = appointment.ends_at.astimezone(
        clinic_timezone
    )

    return CancelAppointmentResponse(
        appointment_id=str(appointment.id),
        status=appointment.status.value,
        starts_at=local_start,
        ends_at=local_end,
        message="Cita cancelada correctamente.",
    )
