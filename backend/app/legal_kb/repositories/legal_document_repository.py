from datetime import date

from sqlalchemy.orm import Session

from app.legal_kb.models.legal_document import LegalDocument, LegalDocumentType


class LegalDocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        title: str,
        document_type: LegalDocumentType,
        source: str,
        official_number: str | None,
        publication_date: date | None,
        original_filename: str,
        storage_key: str,
        mime_type: str,
        file_size: int,
    ) -> LegalDocument:
        document = LegalDocument(
            title=title,
            document_type=document_type,
            source=source,
            official_number=official_number,
            publication_date=publication_date,
            original_filename=original_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=file_size,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_by_id(self, document_id: int) -> LegalDocument | None:
        return self.db.get(LegalDocument, document_id)

    def list(self, skip: int = 0, limit: int = 100) -> list[LegalDocument]:
        return (
            self.db.query(LegalDocument)
            .order_by(LegalDocument.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_status(self, document: LegalDocument, status: str) -> LegalDocument:
        document.status = status
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document: LegalDocument) -> None:
        self.db.delete(document)
        self.db.commit()
