import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.google_drive import upload_excel
from app.models.appointment import Appointment
from app.models.intake import IntakeSubmission
from app.models.patient import Patient
from app.schemas.intake import ExcelUploadResult
from app.services.excel_service import (
    create_patient_workbook,
    create_safe_filename,
)


logger = logging.getLogger(__name__)


async def generate_and_upload_intake_excel(
    db: AsyncSession,
    patient: Patient,
    submission: IntakeSubmission,
    appointment: Appointment | None,
) -> tuple[ExcelUploadResult, str]:
    safe_name = create_safe_filename(
        patient.full_name
    )

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
        submission.excel_web_view_link = (
            uploaded_file.get("web_view_link")
        )
        submission.excel_upload_error = None

        excel_result = ExcelUploadResult(
            status="uploaded",
            filename=filename,
            file_id=uploaded_file["file_id"],
            web_view_link=uploaded_file.get(
                "web_view_link"
            ),
        )

        message = (
            "Formulario registrado y expediente "
            "subido correctamente."
        )

    except Exception:
        logger.exception(
            "No fue posible generar o subir el Excel "
            "de la valoración %s.",
            submission.id,
        )

        submission.excel_upload_status = "failed"
        submission.excel_filename = filename
        submission.excel_file_id = None
        submission.excel_web_view_link = None
        submission.excel_upload_error = (
            "No fue posible generar o subir el "
            "expediente a Google Drive."
        )

        excel_result = ExcelUploadResult(
            status="failed",
            filename=filename,
            error=submission.excel_upload_error,
        )

        message = (
            "Formulario registrado correctamente, "
            "pero el expediente requiere reintentar "
            "su subida."
        )

    db.add(submission)

    try:
        await db.commit()
        await db.refresh(submission)

    except Exception:
        await db.rollback()

        logger.exception(
            "No fue posible guardar los metadatos "
            "del Excel para la valoración %s.",
            submission.id,
        )

    return excel_result, message