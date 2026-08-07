import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.google_drive import upload_excel
from app.models.appointment import (
    Appointment,
    AppointmentStatus,
)
from app.models.intake import IntakeSubmission
from app.models.patient import Patient
from app.schemas.intake import (
     AppointmentResult,
    ExcelUploadResult,
    IntakeSubmissionRequest,
    IntakeSubmissionResponse,
)
from app.services.availability import validate_requested_slot
from app.services.excel_service import (
    create_patient_workbook,
    create_safe_filename,
)
from app.services.agenda_excel_service import (
    sync_new_appointment_to_agenda,
)

logger = logging.getLogger(__name__)
ALARM_KEYS = {
    "loss_of_strength",
    "tingling",
    "numbness",
    "loss_of_sphincter_control",
    "fever",
    "unexplained_weight_loss",
    "severe_night_pain",
}

def calculate_alarm_flag(
    answers: dict[str, dict[str, Any]],
) -> bool:
    alarm_answers = answers.get("alarm_signs", {})

    return any(
        alarm_answers.get(key) is True
        for key in ALARM_KEYS
    )

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
                answers=payload.answers,
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

    # PostgreSQL ya quedó confirmado al salir de db.begin().
    # A partir de aquí generamos y subimos el Excel.

    safe_name = create_safe_filename(patient.full_name)

    filename = (
        f"{safe_name}_"
        f"{submission.assessment_date}_"
        f"{str(submission.id)[:8]}.xlsx"
    )

    try:
        excel_bytes = create_patient_workbook(
            patient=patient,
            submission=submission,
            appointment=appointment,
        )

        uploaded_file = upload_excel(
            excel_bytes=excel_bytes,
            filename=filename,
        )
        submission.excel_upload_status = "uploaded"
        submission.excel_filename = filename
        submission.excel_file_id = uploaded_file["file_id"]
        submission.excel_web_view_link = uploaded_file.get("web_view_link")
        submission.excel_upload_error = None

        excel_result = ExcelUploadResult(
            status="uploaded",
            filename=filename,
            file_id=uploaded_file["file_id"],
            web_view_link=uploaded_file.get(
                "web_view_link"
            ),
        )

        response_message = (
            "Formulario registrado y expediente subido "
            "correctamente."
        )

    except Exception as exc:
        logger.exception(
            "No fue posible generar o subir el Excel "
            "de la valoración %s.",
            submission.id,
        )
        submission.excel_upload_status = "failed"
        submission.excel_filename = filename
        submission.excel_file_id = None
        submission.excel_web_view_link = None
        submission.excel_upload_error = ("No fue posible generar o subir el expediente "
                                         "a Google Drive.")
        excel_result = ExcelUploadResult(
            status="failed",
            filename=filename,
            error=(
                "El formulario quedó registrado, pero el "
                "expediente no pudo subirse a Google Drive."
            ),
        )

        response_message = (
            "Formulario registrado correctamente, pero el "
            "expediente requiere reintentar su subida."
        )
        db.add(submission)

        try:
           await db.commit()
           await db.refresh(submission)
        except Exception:
           await db.rollback()

           logger.exception(
        "No fue posible guardar los metadatos del Excel "
        "para la valoración %s.",
        submission.id,
    )

    db.add(submission)

    try:
        await db.commit()
        await db.refresh(submission)
    except Exception:
        await db.rollback()

        logger.exception(
        "No fue posible guardar los metadatos del Excel "
        "para la valoración %s.",
        submission.id,
    )       
    # AQUÍ VA LA SINCRONIZACIÓN CON agenda.xlsx
    if appointment is not None:
        try:
            sync_new_appointment_to_agenda(
            appointment=appointment,
            patient=patient,
            expediente_url=submission.excel_web_view_link,
        )

        except Exception:
            logger.exception(
            "No fue posible agregar la cita %s "
            "a agenda.xlsx.",
            appointment.id,
        )

    return IntakeSubmissionResponse(
        submission_id=str(submission.id),
        patient_id=str(patient.id),
        appointment=appointment_result,
        alarm_flag=alarm_flag,
        excel=excel_result,
        message=response_message,
    )

