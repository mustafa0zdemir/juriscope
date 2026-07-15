from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class DocumentChunkListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    char_count: int
    token_count: int
    page_number: Optional[int] = None


class DocumentChunkDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    content_id: int
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    token_count: int
    char_count: int
    metadata: dict[str, Any]
