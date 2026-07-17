from dataclasses import asdict, dataclass

from app.retrieval.base import SearchResult


@dataclass(frozen=True)
class LegalCitation:
    source_type: str
    document_type: str | None
    title: str | None
    official_number: str | None
    article: str | None
    court: str | None
    decision_number: str | None
    publication_date: str | None
    page: int | None
    score: float
    document_id: int | None
    chunk_id: int

    @classmethod
    def from_search_result(cls, result: SearchResult) -> "LegalCitation":
        metadata = result.metadata
        return cls(
            source_type="legal",
            document_type=metadata.get("document_type"),
            title=metadata.get("title"),
            official_number=metadata.get("official_number"),
            article=metadata.get("article"),
            court=metadata.get("court"),
            decision_number=metadata.get("decision_number"),
            publication_date=metadata.get("publication_date"),
            page=result.page_number,
            score=result.score,
            document_id=result.document_id,
            chunk_id=result.chunk_id,
        )

    def to_dict(self) -> dict:
        return asdict(self)
