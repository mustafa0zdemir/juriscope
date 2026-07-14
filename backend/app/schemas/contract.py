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
    file_path: str
    mime_type: str
    file_size: int
    status: str
    uploaded_at: datetime
    updated_at: datetime


class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int
