import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.appointment import (
    Appointment,
    AppointmentStatus,
)
from app.models.intake import IntakeSubmission
from app.models.patient import Patient
from app.schemas.intake import (
    AppointmentResult,
    IntakeAnswers,
    IntakeSubmissionRequest,
    IntakeSubmissionResponse,
)
from app.services.availability import validate_requested_slot

from app.services.calendar_service import (
    sync_new_appointment_to_calendar,
)
from app.services.whatsapp_service import (
    notify_clinic_new_appointment,
    notify_patient_new_appointment,
)

logger = logging.getLogger(__name__)

def calculate_alarm_flag(
    answers: IntakeAnswers,
) -> bool:
    return any(answers.signos_alarma.model_dump().values())

async def create_intake_submission(
    db: AsyncSession,
    payload: IntakeSubmissionRequest,
) -> IntakeSubmissionResponse:
    
    appointment_requested = payload.appointment.requested
    requested_start = payload.appointment.starts_at

    if appointment_requested and requested_start is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe seleccionar un horario cuando desea agendar.",
        )

    if not appointment_requested and requested_start is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No debe enviarse un horario si no se solicita cita.",
        )

    local_start = None
    local_end = None

    if requested_start is not None:
        local_start, local_end = validate_requested_slot(
            requested_start
        )

    alarm_flag = calculate_alarm_flag(payload.answers)
    answers = payload.answers.model_dump(mode="json")

    patient: Patient
    submission: IntakeSubmission
    appointment: Appointment | None = None

    try:
        async with db.begin():
            patient = Patient(
                full_name=payload.patient.full_name,
                age=payload.patient.age,
                sex=payload.patient.sex,
                occupation=payload.patient.occupation,
                phone=payload.patient.phone,
            )

            db.add(patient)
            await db.flush()

            submission = IntakeSubmission(
                patient_id=patient.id,
                assessment_date=payload.patient.assessment_date,
                answers=answers,
                alarm_flag=alarm_flag,
                privacy_consent=payload.consents.privacy_consent,
                whatsapp_consent=payload.consents.whatsapp_consent,
            )

            db.add(submission)
            await db.flush()

            appointment_result = AppointmentResult(
                status="not_requested",
            )

            if local_start is not None and local_end is not None:
                occupied_statement = select(
                    Appointment.id
                ).where(
                    Appointment.starts_at == local_start,
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
                        detail=(
                            "El horario seleccionado ya fue reservado."
                        ),
                    )

                appointment = Appointment(
                    patient_id=patient.id,
                    intake_submission_id=submission.id,
                    starts_at=local_start,
                    ends_at=local_end,
                    status=AppointmentStatus.confirmed,
                )

                db.add(appointment)
                await db.flush()

                appointment_result = AppointmentResult(
                    status="confirmed",
                    starts_at=local_start,
                    ends_at=local_end,
                )

    except HTTPException:
        raise

    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El horario fue reservado por otra persona. "
                "Seleccione uno diferente."
            ),
        ) from exc

    # Sincronizacion a calendar
    if appointment is not None:
        await sync_new_appointment_to_calendar(
            db=db,
            appointment=appointment,
            patient=patient,
    )        

    if appointment is not None:
        notify_clinic_new_appointment(
        appointment=appointment,
        patient=patient,
    )

    if appointment is not None:
        notify_patient_new_appointment(
        appointment=appointment,
        patient=patient,
        whatsapp_consent=(
            submission.whatsapp_consent
        ),
    )    
    return IntakeSubmissionResponse(
        submission_id=str(submission.id),
        patient_id=str(patient.id),
        appointment=appointment_result,
        alarm_flag=alarm_flag
    )
