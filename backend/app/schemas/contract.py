from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContractCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    status: str
    uploaded_at: datetime


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    original_filename: str
    stored_filename: str
    storage_key: str
    mime_type: str
    file_size: int
    status: str
    uploaded_at: datetime
    updated_at: datetime


class ContractContentResponse(BaseModel):
    contract_id: int
    page_count: int
    parser: str
    language: str
    text: str


class ContractStatusResponse(BaseModel):
    contract_id: int
    status: str


class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int
