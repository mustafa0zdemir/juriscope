from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.rag.citation_builder import Citation, CitationBuilder
from app.rag.context_builder import ContextBuilder
from app.rag.prompt_builder import PromptBuilder
from app.retrieval.base import SearchResult
from app.schemas.chat import ChatQueryRequest
from app.services.retriever_service import RetrieverService


@dataclass(frozen=True)
class RAGResult:
    question: str
    retrieved_chunks: list[SearchResult]
    constructed_context: str
    constructed_prompt: str
    citations: list[Citation]


class RAGService:
    def __init__(
        self,
        retriever_service: RetrieverService | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        citation_builder: CitationBuilder | None = None,
    ) -> None:
        self.retriever_service = retriever_service or RetrieverService()
        self.context_builder = context_builder or ContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.citation_builder = citation_builder or CitationBuilder()

    def prepare_query(self, db: Session, user_id: int, request: ChatQueryRequest) -> RAGResult:
        chunks = self.retriever_service.retrieve(
            db=db,
            question=request.question,
            user_id=user_id,
            contract_ids=request.contract_ids,
            top_k=request.top_k,
        )
        context = self.context_builder.build(chunks)
        citations = self.citation_builder.build(chunks)
        prompt = self.prompt_builder.build(
            question=request.question,
            context=context,
            citation_labels=[f"[Kaynak {index}]" for index in range(1, len(citations) + 1)],
        )
        return RAGResult(
            question=request.question,
            retrieved_chunks=chunks,
            constructed_context=context,
            constructed_prompt=prompt,
            citations=citations,
        )
