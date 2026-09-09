from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.intake import IntakeSubmission
from app.models.patient import Patient
from app.schemas.records import (
    PaginatedRecordsResponse,
    RecordDetailResponse,
    RecordListItem,
    RecordPatientDetail,
    RecordSubmissionDetail,
)

router = APIRouter(
    prefix="/api/records",
    tags=["Records"],
)

@router.get(
    "",
    response_model=PaginatedRecordsResponse,
)
async def get_records(
    start_date: date,
    end_date: date,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRecordsResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date no puede ser mayor que end_date",
        )

    filters = (
        IntakeSubmission.assessment_date >= start_date,
        IntakeSubmission.assessment_date <= end_date,
    )

    total_query = (
        select(func.count())
        .select_from(IntakeSubmission)
        .join(Patient, Patient.id == IntakeSubmission.patient_id)
        .where(*filters)
    )
    total = (await db.execute(total_query)).scalar_one()

    records_query = (
        select(
            IntakeSubmission.id.label("submission_id"),
            Patient.id.label("patient_id"),
            Patient.full_name,
            Patient.age,
            Patient.sex,
            Patient.occupation,
            IntakeSubmission.assessment_date,
            IntakeSubmission.alarm_flag,
        )
        .select_from(IntakeSubmission)
        .join(Patient, Patient.id == IntakeSubmission.patient_id)
        .where(*filters)
        .order_by(
            IntakeSubmission.assessment_date.desc(),
            IntakeSubmission.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(records_query)).mappings().all()

    return PaginatedRecordsResponse(
        items=[RecordListItem(**row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )

@router.get(
    "/{submission_id}",
    response_model=RecordDetailResponse,
)
async def get_record_detail(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RecordDetailResponse:
    detail_query = (
        select(
            Patient.id.label("patient_id"),
            Patient.full_name,
            Patient.age,
            Patient.sex,
            Patient.occupation,
            Patient.phone,
            IntakeSubmission.id.label("submission_id"),
            IntakeSubmission.assessment_date,
            IntakeSubmission.answers,
            IntakeSubmission.alarm_flag,
        )
        .select_from(IntakeSubmission)
        .join(Patient, Patient.id == IntakeSubmission.patient_id)
        .where(IntakeSubmission.id == submission_id)
    )
    row = (await db.execute(detail_query)).mappings().one_or_none()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró la valoración seleccionada.",
        )

    patient = RecordPatientDetail(
        patient_id=row["patient_id"],
        full_name=row["full_name"],
        age=row["age"],
        sex=row["sex"],
        occupation=row["occupation"],
        phone=row["phone"],
    )
    submission = RecordSubmissionDetail(
        submission_id=row["submission_id"],
        patient_id=row["patient_id"],
        assessment_date=row["assessment_date"],
        answers=row["answers"],
        alarm_flag=row["alarm_flag"],
    )

    return RecordDetailResponse(
        patient=patient,
        submission=submission,
    )
