"""add legal knowledge base

Revision ID: 5f4d2a1c8b90
Revises: 2c7c8a0e9f11
Create Date: 2026-07-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5f4d2a1c8b90"
down_revision: Union[str, Sequence[str], None] = "2c7c8a0e9f11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(sa.text("UPDATE users SET is_admin = true WHERE username = 'admin'"))

    op.create_table(
        "legal_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("document_type", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=False),
        sa.Column("official_number", sa.String(length=100), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="tr"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="uploaded"),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_legal_documents_title", "legal_documents", ["title"])
    op.create_index("ix_legal_documents_document_type", "legal_documents", ["document_type"])
    op.create_index("ix_legal_documents_official_number", "legal_documents", ["official_number"])
    op.create_index("ix_legal_documents_status", "legal_documents", ["status"])

    op.create_table(
        "legal_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("embedding_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["legal_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_chunks_document_id", "legal_chunks", ["document_id"])
    op.create_index("ix_legal_chunks_embedding_status", "legal_chunks", ["embedding_status"])


def downgrade() -> None:
    op.drop_index("ix_legal_chunks_embedding_status", table_name="legal_chunks")
    op.drop_index("ix_legal_chunks_document_id", table_name="legal_chunks")
    op.drop_table("legal_chunks")
    op.drop_index("ix_legal_documents_status", table_name="legal_documents")
    op.drop_index("ix_legal_documents_official_number", table_name="legal_documents")
    op.drop_index("ix_legal_documents_document_type", table_name="legal_documents")
    op.drop_index("ix_legal_documents_title", table_name="legal_documents")
    op.drop_table("legal_documents")
    op.drop_column("users", "is_admin")
