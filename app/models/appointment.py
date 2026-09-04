import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Index,
    func,
)
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from datetime import datetime

from pydantic import BaseModel

class AvailableSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime
    label: str

class AvailabilityResponse(BaseModel):
    timezone: str
    slots: list[AvailableSlot]

class AppointmentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"

class Appointment(Base):
    __tablename__ = "appointments"

    __table_args__ = (
    Index(
        "uq_appointments_active_starts_at",
        "starts_at",
        unique=True,
        postgresql_where=text(
            "status IN ('pending', 'confirmed')"
        ),
    ),
)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    intake_submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intake_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            name="appointment_status",
        ),
        nullable=False,
        default=AppointmentStatus.confirmed,
    )

    calendar_event_id: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    patient = relationship(
        "Patient",
        back_populates="appointments",
    )

    intake_submission = relationship(
        "IntakeSubmission",
        back_populates="appointment",
    )

    google_calendar_event_id: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,)

    google_calendar_event_link: Mapped[str | None] = mapped_column(
    String(1000),
    nullable=True,)

    google_calendar_sync_status: Mapped[str] = mapped_column(
    String(30),
    nullable=False,
    default="pending",)