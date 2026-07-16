from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ChatMessageBase(BaseModel):
    role: str
    content: str
    model: str | None = None
    latency_ms: int | None = None


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
