from enum import Enum

from pydantic import BaseModel, Field

from app.config.settings import settings


class SearchMode(str, Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Doğal dil sorgusu")
    contract_id: int | None = Field(None, description="Belirli bir sözleşmeye filtrele (opsiyonel)")
    top_k: int = Field(5, ge=1, le=20, description="Döndürülecek maksimum sonuç sayısı")
    search_mode: SearchMode = Field(
        default=SearchMode(settings.default_search_mode),
        description="Arama modu: vector, keyword veya hybrid",
    )


class SearchResultItem(BaseModel):
    score: float
    chunk_id: int
    contract_id: int
    chunk_index: int
    page_number: int | None
    text: str
    metadata: dict
    vector_score: float | None = None
    keyword_score: float | None = None


class SearchDebugResponse(BaseModel):
    vector_hits: list[SearchResultItem]
    keyword_hits: list[SearchResultItem]
    merged_hits: list[SearchResultItem]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int
    debug: SearchDebugResponse | None = None
