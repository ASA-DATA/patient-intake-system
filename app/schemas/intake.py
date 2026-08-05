from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PatientData(BaseModel):
    full_name: str = Field(min_length=3, max_length=200)
    age: int = Field(ge=1, le=120)
    sex: str = Field(min_length=1, max_length=50)
    occupation: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=10, max_length=30)
    assessment_date: date

    @field_validator("full_name", "sex", "occupation", "phone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Este campo no puede estar vacío.")

        return value


class AppointmentRequest(BaseModel):
    requested: bool
    starts_at: datetime | None = None

    @field_validator("starts_at")
    @classmethod
    def validate_starts_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError(
                "La fecha de la cita debe incluir zona horaria."
            )

        return value


class ConsentData(BaseModel):
    privacy_consent: bool
    whatsapp_consent: bool

    @field_validator("privacy_consent")
    @classmethod
    def privacy_must_be_accepted(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "El aviso de privacidad debe ser aceptado."
            )

        return value


class IntakeSubmissionRequest(BaseModel):
    patient: PatientData

    answers: dict[str, dict[str, Any]]

    appointment: AppointmentRequest

    consents: ConsentData

    @field_validator("answers")
    @classmethod
    def answers_must_not_be_empty(
        cls,
        value: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        if not value:
            raise ValueError(
                "Las respuestas del formulario son obligatorias."
            )

        return value


class AppointmentResult(BaseModel):
    status: Literal["not_requested", "confirmed"]
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class IntakeSubmissionResponse(BaseModel):
    submission_id: str
    patient_id: str
    appointment: AppointmentResult
    alarm_flag: bool
    message: str