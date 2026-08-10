"""add google calendar metadata to appointments

Revision ID: dcae255f22ea
Revises: c3100a8363c3
Create Date: 2026-08-07 13:51:12.631282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dcae255f22ea'
down_revision: Union[str, Sequence[str], None] = 'c3100a8363c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "appointments",
        sa.Column(
            "google_calendar_event_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "appointments",
        sa.Column(
            "google_calendar_event_link",
            sa.String(length=1000),
            nullable=True,
        ),
    )

    op.add_column(
        "appointments",
        sa.Column(
            "google_calendar_sync_status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
    )

    op.alter_column(
        "appointments",
        "google_calendar_sync_status",
        server_default=None,
    )

def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column(
        "appointments",
        "google_calendar_sync_status",
    )

    op.drop_column(
        "appointments",
        "google_calendar_event_link",
    )

    op.drop_column(
        "appointments",
        "google_calendar_event_id",
    )