from dataclasses import asdict, dataclass

from app.retrieval.base import SearchResult


@dataclass(frozen=True)
class Citation:
    contract_id: int
    chunk_id: int
    chunk_index: int
    page_number: int | None
    score: float

    @classmethod
    def from_search_result(cls, result: SearchResult) -> "Citation":
        return cls(
            contract_id=result.contract_id,
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            page_number=result.page_number,
            score=result.score,
        )

    def to_dict(self) -> dict[str, int | float | None]:
        return asdict(self)


class CitationBuilder:
    def build(self, chunks: list[SearchResult]) -> list[Citation]:
        return [Citation.from_search_result(chunk) for chunk in chunks]
