from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum as SqlEnum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.legal_kb.models.legal_chunk import LegalChunk


class LegalDocumentType(str, Enum):
    LAW = "LAW"
    REGULATION = "REGULATION"
    COMMUNIQUE = "COMMUNIQUE"
    SUPREME_COURT = "SUPREME_COURT"
    COUNCIL_OF_STATE = "COUNCIL_OF_STATE"
    CONSTITUTIONAL_COURT = "CONSTITUTIONAL_COURT"
    OTHER = "OTHER"


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    document_type: Mapped[LegalDocumentType] = mapped_column(
        SqlEnum(LegalDocumentType, name="legal_document_type", native_enum=False),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    official_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="tr")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded", index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    chunks: Mapped[list["LegalChunk"]] = relationship(
        "LegalChunk", back_populates="document", cascade="all, delete-orphan"
    )
