from typing import Any

from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


class DocumentChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_bulk(
        self,
        contract_id: int,
        content_id: int,
        chunks_data: list[dict[str, Any]],
    ) -> list[DocumentChunk]:
        """
        Creates multiple DocumentChunk records in bulk.
        chunks_data should be a list of dicts with keys:
        'chunk_index', 'text', 'page_number', 'token_count', 'char_count', 'metadata'
        """
        chunks = [
            DocumentChunk(
                contract_id=contract_id,
                content_id=content_id,
                chunk_index=data["chunk_index"],
                text=data["text"],
                page_number=data.get("page_number"),
                token_count=data["token_count"],
                char_count=data["char_count"],
                metadata_=data.get("metadata", {}),
            )
            for data in chunks_data
        ]
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def list_by_contract_id(self, contract_id: int) -> list[DocumentChunk]:
        return (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.contract_id == contract_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

    def get_by_id(self, chunk_id: int) -> DocumentChunk | None:
        return self.db.get(DocumentChunk, chunk_id)
