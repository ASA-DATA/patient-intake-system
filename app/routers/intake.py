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