from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.legal_kb.models.legal_document import LegalDocumentType


class LegalDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    document_type: LegalDocumentType
    source: str
    official_number: str | None
    publication_date: date | None
    language: str
    status: str
    original_filename: str
    file_size: int
    created_at: datetime
    updated_at: datetime


class LegalDocumentListResponse(BaseModel):
    items: list[LegalDocumentResponse]
    total: int
