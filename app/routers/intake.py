from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.schemas.intake import (
    IntakeSubmissionRequest,
    IntakeSubmissionResponse,
)
from app.services.intake_service import (
    create_intake_submission,
)

from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.intake import IntakeSubmission
from app.services.excel_service import create_patient_workbook
from app.services.excel_service import (
    create_patient_workbook,
    create_safe_filename,
)

router = APIRouter(
    prefix="/api/intake",
    tags=["Patient intake"],
)


@router.post(
    "/submit",
    response_model=IntakeSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_intake(
    payload: IntakeSubmissionRequest,
    db: AsyncSession = Depends(get_db),
) -> IntakeSubmissionResponse:
    return await create_intake_submission(
        db=db,
        payload=payload,
    )

@router.get("/{submission_id}/excel")
async def download_intake_excel(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(IntakeSubmission)
        .options(
            selectinload(IntakeSubmission.patient),
            selectinload(IntakeSubmission.appointment),
        )
        .where(IntakeSubmission.id == submission_id)
    )

    result = await db.execute(statement)
    submission = result.scalar_one_or_none()

    if submission is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Formulario no encontrado.",
        )

    excel_bytes = create_patient_workbook(
        patient=submission.patient,
        submission=submission,
        appointment=submission.appointment,
    )

    

    safe_name = create_safe_filename(submission.patient.full_name) 
    filename = f"{safe_name}_{submission.assessment_date}.xlsx"

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )