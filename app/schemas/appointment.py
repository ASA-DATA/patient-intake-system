from datetime import datetime

from pydantic import BaseModel, field_validator

class CancelAppointmentResponse(BaseModel):
    appointment_id: str
    status: str
    starts_at: datetime
    ends_at: datetime
    message: str

class AvailableSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime
    label: str

class AvailabilityResponse(BaseModel):
    timezone: str
    slots: list[AvailableSlot]

class RescheduleAppointmentRequest(BaseModel):
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "La fecha debe incluir zona horaria."
            )

        return value


class RescheduleAppointmentResponse(BaseModel):
    appointment_id: str
    status: str
    starts_at: datetime
    ends_at: datetime
    message: str    

class CancelAppointmentResponse(BaseModel):
    appointment_id: str
    status: str
    starts_at: datetime
    ends_at: datetime
    message: str    