from sqlalchemy.orm import Session

from app.legal_kb.models.legal_document import LegalDocumentType
from app.legal_kb.repositories.legal_chunk_repository import LegalChunkRepository
from app.retrieval.base import SearchResult
from app.services.bm25_service import BM25Service


class LegalBM25Service:
    def __init__(self, repository: LegalChunkRepository | None = None) -> None:
        self.repository = repository

    def search(
        self,
        db: Session,
        question: str,
        top_k: int,
        document_types: list[LegalDocumentType] | None = None,
    ) -> list[SearchResult]:
        chunks = (self.repository or LegalChunkRepository(db)).list_searchable(document_types)
        query_tokens = BM25Service.tokenize(question)
        if not chunks or not query_tokens:
            return []

        documents = [BM25Service.tokenize(chunk.text) for chunk in chunks]
        scores = BM25Service._score(query_tokens, documents)
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        results: list[SearchResult] = []
        for index, score in ranked[:top_k]:
            if score <= 0:
                continue
            chunk = chunks[index]
            results.append(
                SearchResult(
                    score=score,
                    chunk_id=chunk.id,
                    contract_id=None,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    metadata={**chunk.metadata_},
                    keyword_score=score,
                    bm25_score=score,
                    source_type="legal",
                    document_id=chunk.document_id,
                )
            )
        return results
