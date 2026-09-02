from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.intake import IntakeSubmission
from app.models.appointment import Appointment
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


def model_to_dict(obj):
    return {
        column.name: getattr(obj, column.name)
        for column in obj.__table__.columns
    }


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
    "/by-date",
    deprecated=True,
    description=(
        "Endpoint obsoleto conservado temporalmente para el frontend desplegado. "
        "Debe eliminarse después de desplegar el nuevo frontend paginado."
    ),
)
async def get_records_by_date(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date no puede ser mayor que end_date",
        )

    start_datetime = datetime.combine(
        start_date,
        time.min,
    )

    end_datetime = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
    )

    # =============================
    # PATIENTS
    # =============================

    patients_query = (
        select(Patient)
        .where(
            Patient.created_at >= start_datetime - timedelta(days=10),
            Patient.created_at <= end_datetime,
        )
        .order_by(Patient.created_at)
    )

    patients_result = await db.execute(
        patients_query
    )

    patients = patients_result.scalars().all()

    # =============================
    # INTAKE SUBMISSIONS
    # =============================

    intake_query = (
        select(IntakeSubmission)
        .where(
            IntakeSubmission.created_at >= start_datetime - timedelta(days=10),
            IntakeSubmission.created_at <= end_datetime,
        )
        .order_by(IntakeSubmission.created_at)
    )

    intake_result = await db.execute(
        intake_query
    )

    intake_submissions = intake_result.scalars().all()
       
    # =============================
    # APPOINTMENT
    # =============================

    appointment_query = (
        select(Appointment)
        .where(
            Appointment.starts_at >= start_datetime,
            Appointment.starts_at <= end_datetime,
        )
        .order_by(Appointment.starts_at)
    )

    appointment_result = await db.execute(
        appointment_query
    )

    appointments = appointment_result.scalars().all()

    return {
        "start_date": start_date,
        "end_date": end_date,
        "patients": [
            model_to_dict(patient)
            for patient in patients
        ],
        "intake_submissions": [
            model_to_dict(submission)
            for submission in intake_submissions
        ],
        "appointments": [
            model_to_dict(appointment)
            for appointment in appointments
        ]
    }


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
