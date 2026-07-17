from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import NotFoundException
from app.legal_kb.models.legal_document import LegalDocument
from app.legal_kb.repositories.legal_document_repository import LegalDocumentRepository
from app.legal_kb.schemas.legal_document import LegalDocumentListResponse, LegalDocumentResponse
from app.storage.qdrant_service import QdrantService
from app.storage.storage_service import StorageService


class LegalDocumentService:
    def list_documents(self, db: Session, skip: int = 0, limit: int = 100) -> LegalDocumentListResponse:
        documents = LegalDocumentRepository(db).list(skip=skip, limit=limit)
        return LegalDocumentListResponse(
            items=[LegalDocumentResponse.model_validate(document) for document in documents],
            total=len(documents),
        )

    def get_document(self, db: Session, document_id: int) -> LegalDocumentResponse:
        return LegalDocumentResponse.model_validate(self._get_document(db, document_id))

    def delete_document(
        self,
        db: Session,
        document_id: int,
        storage: StorageService,
    ) -> None:
        repository = LegalDocumentRepository(db)
        document = self._get_document(db, document_id)
        storage.delete(document.storage_key)
        QdrantService(settings.legal_collection).delete_by_payload("document_id", document.id)
        repository.delete(document)

    @staticmethod
    def _get_document(db: Session, document_id: int) -> LegalDocument:
        document = LegalDocumentRepository(db).get_by_id(document_id)
        if not document:
            raise NotFoundException(detail="Legal belge bulunamadı")
        return document
