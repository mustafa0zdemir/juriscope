"""add citations to chat messages

Revision ID: 2c7c8a0e9f11
Revises: 971966826b06
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c7c8a0e9f11"
down_revision: Union[str, Sequence[str], None] = "971966826b06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("citations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "citations")
