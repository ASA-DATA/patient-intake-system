"""add assessment date index

Revision ID: 8f4c2a1d9b7e
Revises: 6606bfd66c87
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8f4c2a1d9b7e"
down_revision: Union[str, Sequence[str], None] = "6606bfd66c87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the index used by paginated record date-range queries."""
    op.create_index(
        "ix_intake_submissions_assessment_date",
        "intake_submissions",
        ["assessment_date"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the record assessment-date index."""
    op.drop_index(
        "ix_intake_submissions_assessment_date",
        table_name="intake_submissions",
    )
