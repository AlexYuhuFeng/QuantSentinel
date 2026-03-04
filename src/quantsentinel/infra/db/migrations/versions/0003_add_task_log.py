"""add task log column

Revision ID: 0003_add_task_log
Revises: 0002_add_notifications
Create Date: 2026-03-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_add_task_log"
down_revision = "0002_add_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("log", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "log")
