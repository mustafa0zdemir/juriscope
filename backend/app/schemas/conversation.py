from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.chat import CitationResponse


class ChatMessageBase(BaseModel):
    role: str
    content: str
    model: str | None = None
    latency_ms: int | None = None
    citations: list[CitationResponse] = Field(default_factory=list)

    @field_validator("citations", mode="before")
    @classmethod
    def normalize_citations(cls, value):
        return value or []


class ChatMessageResponse(ChatMessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ConversationBase(BaseModel):
    title: str


class ConversationCreate(ConversationBase):
    pass


class ConversationResponse(ConversationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: list[ChatMessageResponse] = []
