from datetime import datetime

from pydantic import BaseModel


class AvailableSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime
    label: str


class AvailabilityResponse(BaseModel):
    timezone: str
    slots: list[AvailableSlot]