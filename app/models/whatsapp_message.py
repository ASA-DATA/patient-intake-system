import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WhatsAppRecipientType(str, Enum):
    clinic = "clinic"
    patient = "patient"


class WhatsAppMessageType(str, Enum):
    confirmation = "confirmation"
    reschedule = "reschedule"
    cancellation = "cancellation"


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "appointments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    recipient_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    message_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    message_sid: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
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