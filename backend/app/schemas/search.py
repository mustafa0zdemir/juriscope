from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Doğal dil sorgusu")
    contract_id: int | None = Field(None, description="Belirli bir sözleşmeye filtrele (opsiyonel)")
    top_k: int = Field(5, ge=1, le=20, description="Döndürülecek maksimum sonuç sayısı")


class SearchResultItem(BaseModel):
    score: float
    chunk_id: int
    contract_id: int
    chunk_index: int
    page_number: int | None
    text: str
    metadata: dict


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int
