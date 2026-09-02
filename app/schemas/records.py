from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RecordListItem(BaseModel):
    submission_id: UUID
    patient_id: UUID
    full_name: str
    age: int
    sex: str
    occupation: str
    assessment_date: date
    alarm_flag: bool


class PaginatedRecordsResponse(BaseModel):
    items: list[RecordListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class RecordPatientDetail(BaseModel):
    patient_id: UUID
    full_name: str
    age: int
    sex: str
    occupation: str
    phone: str


class RecordSubmissionDetail(BaseModel):
    submission_id: UUID
    patient_id: UUID
    assessment_date: date
    answers: dict[str, Any]
    alarm_flag: bool


class RecordDetailResponse(BaseModel):
    patient: RecordPatientDetail
    submission: RecordSubmissionDetail


class AppointmentListItem(BaseModel):
    appointment_id: UUID
    intake_submission_id: UUID
    patient_id: UUID
    patient_name: str
    phone: str
    starts_at: datetime
    ends_at: datetime
    status: str


class PaginatedAppointmentsResponse(BaseModel):
    items: list[AppointmentListItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
