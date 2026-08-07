import uuid
from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IntakeSubmission(Base):
    __tablename__ = "intake_submissions"

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

    assessment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    answers: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    alarm_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    privacy_consent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    whatsapp_consent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    patient = relationship(
        "Patient",
        back_populates="submissions",
    )

    appointment = relationship(
        "Appointment",
        back_populates="intake_submission",
        uselist=False,
    )

    excel_upload_status: Mapped[str] = mapped_column(
    String(30),
    nullable=False,
    default="pending",
    )

    excel_filename: Mapped[str | None] = mapped_column(
    String(300),
    nullable=True,
    )

    excel_file_id: Mapped[str | None] = mapped_column(
    String(300),
    nullable=True,
    )

    excel_web_view_link: Mapped[str | None] = mapped_column(
    String(1000),
    nullable=True,
    )

    excel_upload_error: Mapped[str | None] = mapped_column(
    String(1000),
    nullable=True,
    )