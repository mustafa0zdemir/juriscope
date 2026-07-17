from dataclasses import dataclass
from collections.abc import Iterator
import logging
from time import perf_counter

from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.rag.citation_builder import Citation, CitationBuilder
from app.rag.context_builder import ContextBuilder
from app.rag.prompt_builder import PromptBuilder
from app.retrieval.base import SearchResult
from app.schemas.chat import ChatQueryRequest
from app.services.llm_service import LLMService
from app.services.retriever_service import RetrieverService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RAGResult:
    question: str
    retrieved_chunks: list[SearchResult]
    constructed_context: str
    constructed_prompt: str
    citations: list[Citation]


@dataclass(frozen=True)
class RAGAnswerResult:
    question: str
    answer: str
    citations: list[Citation]
    used_chunks: list[SearchResult]
    model: str
    latency_ms: int


@dataclass(frozen=True)
class RAGStreamEvent:
    event: str
    data: dict


class RAGService:
    def __init__(
        self,
        retriever_service: RetrieverService | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        citation_builder: CitationBuilder | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.retriever_service = retriever_service or RetrieverService()
        self.context_builder = context_builder or ContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.citation_builder = citation_builder or CitationBuilder()
        self.llm_service = llm_service or LLMService()

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

    def query(self, db: Session, user_id: int, request: ChatQueryRequest) -> RAGAnswerResult:
        started_at = perf_counter()
        prepared = self.prepare_query(db=db, user_id=user_id, request=request)
        answer = self.llm_service.generate(prepared.constructed_prompt)
        citations = self.citation_builder.build(prepared.retrieved_chunks)
        latency_ms = round((perf_counter() - started_at) * 1000)
        return RAGAnswerResult(
            question=prepared.question,
            answer=answer,
            citations=citations,
            used_chunks=prepared.retrieved_chunks,
            model=self.llm_service.model_name,
            latency_ms=latency_ms,
        )

    def stream_query(
        self,
        db: Session,
        user_id: int,
        request: ChatQueryRequest,
        conversation_id: int,
    ) -> Iterator[RAGStreamEvent]:
        started_at = perf_counter()
        try:
            prepared = self.prepare_query(db=db, user_id=user_id, request=request)
            yield RAGStreamEvent("start", {"conversation_id": conversation_id})
            answer_parts: list[str] = []

            try:
                for text in self.llm_service.generate_stream(prepared.constructed_prompt):
                    if text:
                        answer_parts.append(text)
                        yield RAGStreamEvent("token", {"text": text})
            except GeneratorExit:
                logger.info("Streaming connection closed before completion")
                return
            except Exception as exc:
                logger.exception("RAG streaming failed")
                yield RAGStreamEvent("error", self._stream_error(exc))
                return

            answer = "".join(answer_parts).strip()
            if not answer:
                yield RAGStreamEvent(
                    "error", {"code": "empty_response", "message": "LLM boş cevap döndürdü"}
                )
                return

            citations = self.citation_builder.build(prepared.retrieved_chunks)
            citation_data = [citation.to_dict() for citation in citations]
            latency_ms = round((perf_counter() - started_at) * 1000)

            try:
                from app.services.conversation_service import ConversationService

                ConversationService().add_message(
                    db=db,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer,
                    model=self.llm_service.model_name,
                    latency_ms=latency_ms,
                    citations=citation_data,
                )
            except Exception:
                logger.exception("Streaming assistant message could not be saved")
                yield RAGStreamEvent(
                    "error",
                    {"code": "persistence_error", "message": "Cevap kaydedilemedi"},
                )
                return

            yield RAGStreamEvent("citations", {"citations": citation_data})
            yield RAGStreamEvent(
                "done",
                {
                    "conversation_id": conversation_id,
                    "model": self.llm_service.model_name,
                    "latency_ms": latency_ms,
                },
            )
        except GeneratorExit:
            logger.info("Streaming connection closed before preparation completed")
        except Exception as exc:
            logger.exception("RAG stream preparation failed")
            yield RAGStreamEvent("error", self._stream_error(exc))

    @staticmethod
    def _stream_error(exc: Exception) -> dict[str, str]:
        if isinstance(exc, HTTPException):
            detail = str(exc.detail)
            code = str(exc.status_code)
        else:
            detail = "Streaming sırasında beklenmeyen bir hata oluştu"
            code = "stream_error"
        return {"code": code, "message": detail}
