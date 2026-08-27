from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.models.patient import Patient
from app.models.intake import IntakeSubmission
from app.models.appointment import Appointment

router = APIRouter(
    prefix="/api/records",
    tags=["Records"],
)


def model_to_dict(obj):
    return {
        column.name: getattr(obj, column.name)
        for column in obj.__table__.columns
    }


@router.get("/by-date")
async def get_records_by_date(
    start_date: date,
    end_date: date,
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

    async with AsyncSessionFactory() as session:

        # =============================
        # PATIENTS
        # =============================

        patients_query = (
            select(Patient)
            .where(
                Patient.created_at >= start_datetime,
                Patient.created_at < end_datetime,
            )
            .order_by(Patient.created_at)
        )

        patients_result = await session.execute(
            patients_query
        )

        patients = patients_result.scalars().all()

        # =============================
        # INTAKE SUBMISSIONS
        # =============================

        intake_query = (
            select(IntakeSubmission)
            .where(
                IntakeSubmission.created_at >= start_datetime,
                IntakeSubmission.created_at < end_datetime,
            )
            .order_by(IntakeSubmission.created_at)
        )

        intake_result = await session.execute(
            intake_query
        )

        intake_submissions = intake_result.scalars().all()
       
        # =============================
        # APPOINTMENT
        # =============================

        appointment_query= (
            select(Appointment)
            .where(
                Appointment.starts_at >= start_datetime,
                Appointment.starts_at < end_datetime,
            )
            .order_by(Appointment.starts_at)
        )

        appointment_result=await session.execute(
            appointment_query
        )

        appointments =appointment_result.scalars().all()

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