from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.legal_kb.models.legal_chunk import LegalChunk
from app.legal_kb.models.legal_document import LegalDocument, LegalDocumentType


class LegalChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_bulk(self, document_id: int, chunks_data: list[dict[str, Any]]) -> list[LegalChunk]:
        chunks = [
            LegalChunk(
                document_id=document_id,
                chunk_index=data["chunk_index"],
                text=data["text"],
                page_number=data.get("page_number"),
                token_count=data["token_count"],
                metadata_=data.get("metadata", {}),
                embedding_status=data.get("embedding_status", "pending"),
            )
            for data in chunks_data
        ]
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def list_by_document_id(self, document_id: int) -> list[LegalChunk]:
        return (
            self.db.query(LegalChunk)
            .filter(LegalChunk.document_id == document_id)
            .order_by(LegalChunk.chunk_index.asc())
            .all()
        )

    def list_searchable(
        self,
        document_types: list[LegalDocumentType] | None = None,
    ) -> list[LegalChunk]:
        query = (
            self.db.query(LegalChunk)
            .options(joinedload(LegalChunk.document))
            .join(LegalDocument)
            .filter(LegalDocument.status == "embedded")
        )
        if document_types:
            query = query.filter(LegalDocument.document_type.in_(document_types))
        return query.order_by(LegalChunk.document_id.asc(), LegalChunk.chunk_index.asc()).all()

    def mark_embedded(self, chunks: list[LegalChunk]) -> None:
        for chunk in chunks:
            chunk.embedding_status = "embedded"
        self.db.commit()
