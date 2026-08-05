import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    full_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sex: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    occupation: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
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

    submissions = relationship(
        "IntakeSubmission",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    appointments = relationship(
        "Appointment",
        back_populates="patient",
        cascade="all, delete-orphan",
    )