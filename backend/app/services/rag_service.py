from dataclasses import dataclass
from collections.abc import Iterator
import logging
from time import perf_counter

from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.rag.citation_builder import Citation, CitationBuilder
from app.legal_kb.models.legal_citation import LegalCitation
from app.rag.multi_source_context_builder import MultiSourceContextBuilder
from app.rag.prompt_builder import PromptBuilder
from app.config.settings import settings
from app.retrieval.base import SearchResult
from app.retrieval.hybrid_retriever import RetrievalDebug
from app.schemas.chat import ChatQueryRequest
from app.services.llm_service import LLMService
from app.services.multi_source_retriever_service import MultiSourceRetrieverService
from app.trustworthy_rag.schemas import (
    CitationCoverage,
    GroundingResult,
    GuardrailReport,
    HallucinationRisk,
    InsufficientContextResponse,
    RAGDebugResponse,
    RetrievalMetrics,
)
from app.trustworthy_rag.services.citation_coverage_validator import CitationCoverageValidator
from app.trustworthy_rag.services.grounding_validator import GroundingValidator
from app.trustworthy_rag.services.hallucination_risk_service import HallucinationRiskService
from app.trustworthy_rag.services.rag_guard_service import RAGGuardService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RAGResult:
    question: str
    retrieved_chunks: list[SearchResult]
    constructed_context: str
    constructed_prompt: str
    citations: list[Citation | LegalCitation]
    retrieval_debug: RetrievalDebug | None = None
    guardrails: GuardrailReport | None = None
    retrieval_metrics: RetrievalMetrics | None = None
    context_sufficient: bool = True


@dataclass(frozen=True)
class RAGAnswerResult:
    question: str
    answer: str
    citations: list[Citation | LegalCitation]
    used_chunks: list[SearchResult]
    model: str
    latency_ms: int
    retrieval_debug: RetrievalDebug | None = None
    guardrails: GuardrailReport | None = None
    grounding: GroundingResult | None = None
    citation_coverage: CitationCoverage | None = None
    hallucination_risk: HallucinationRisk | None = None
    retrieval_metrics: RetrievalMetrics | None = None
    context_sufficient: bool = True
    confidence: int | None = None


@dataclass(frozen=True)
class RAGStreamEvent:
    event: str
    data: dict


class RAGService:
    def __init__(
        self,
        retriever_service: MultiSourceRetrieverService | None = None,
        context_builder: MultiSourceContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        citation_builder: CitationBuilder | None = None,
        llm_service: LLMService | None = None,
        guard_service: RAGGuardService | None = None,
        grounding_validator: GroundingValidator | None = None,
        citation_validator: CitationCoverageValidator | None = None,
        hallucination_service: HallucinationRiskService | None = None,
    ) -> None:
        self.retriever_service = retriever_service or MultiSourceRetrieverService()
        self.context_builder = context_builder or MultiSourceContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.citation_builder = citation_builder or CitationBuilder()
        self.llm_service = llm_service or LLMService()
        self.guard_service = guard_service or RAGGuardService()
        self.grounding_validator = grounding_validator or GroundingValidator()
        self.citation_validator = citation_validator or CitationCoverageValidator()
        self.hallucination_service = hallucination_service or HallucinationRiskService()

    def prepare_query(self, db: Session, user_id: int, request: ChatQueryRequest) -> RAGResult:
        chunks, retrieval_debug = self._retrieve_chunks(
            db=db,
            user_id=user_id,
            request=request,
        )
        context = self.context_builder.build(chunks)
        citations = self.citation_builder.build(chunks)
        guardrails, retrieval_metrics = self.guard_service.evaluate(
            question=request.question,
            chunks=chunks,
            context=context,
            search_mode=request.search_mode.value,
        )
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
            retrieval_debug=retrieval_debug if settings.enable_debug_search else None,
            guardrails=guardrails,
            retrieval_metrics=retrieval_metrics,
            context_sufficient=guardrails.passed,
        )

    def query(
        self,
        db: Session,
        user_id: int,
        request: ChatQueryRequest,
    ) -> RAGAnswerResult | InsufficientContextResponse:
        started_at = perf_counter()
        prepared = self.prepare_query(db=db, user_id=user_id, request=request)
        if not prepared.context_sufficient:
            return self._insufficient(prepared)
        answer = self.llm_service.generate(prepared.constructed_prompt)
        grounding, coverage, hallucination, confidence = self._validate_answer(answer, prepared)
        latency_ms = round((perf_counter() - started_at) * 1000)
        return RAGAnswerResult(
            question=prepared.question,
            answer=answer,
            citations=prepared.citations,
            used_chunks=prepared.retrieved_chunks,
            model=self.llm_service.model_name,
            latency_ms=latency_ms,
            retrieval_debug=prepared.retrieval_debug,
            guardrails=prepared.guardrails,
            grounding=grounding,
            citation_coverage=coverage,
            hallucination_risk=hallucination,
            retrieval_metrics=prepared.retrieval_metrics,
            context_sufficient=True,
            confidence=confidence,
        )

    def debug_query(self, db: Session, user_id: int, request: ChatQueryRequest) -> RAGDebugResponse:
        prepared = self.prepare_query(db=db, user_id=user_id, request=request)
        answer: str | None = None
        grounding = None
        coverage = None
        hallucination = None
        if prepared.context_sufficient:
            answer = self.llm_service.generate(prepared.constructed_prompt)
            grounding, coverage, hallucination, _ = self._validate_answer(answer, prepared)
        debug = self._debug_to_dict(prepared.retrieval_debug) or {
            "used_chunks": [chunk.__dict__ for chunk in prepared.retrieved_chunks]
        }
        return RAGDebugResponse(
            retrieval=debug,
            rerank={
                "enabled": request.rerank and settings.rerank_enabled,
                "hits": prepared.retrieval_metrics.reranked_chunks if prepared.retrieval_metrics else 0,
            },
            context=prepared.constructed_context,
            guardrails=prepared.guardrails,
            prompt=prepared.constructed_prompt,
            grounding=grounding,
            citation_coverage=coverage,
            hallucination_risk=hallucination,
            llm_answer=answer,
            context_sufficient=prepared.context_sufficient,
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
            if not prepared.context_sufficient:
                insufficient = self._insufficient(prepared)
                yield RAGStreamEvent("guardrails", insufficient.model_dump(mode="json"))
                yield RAGStreamEvent(
                    "done",
                    {
                        "conversation_id": conversation_id,
                        "status": insufficient.status,
                        "context_sufficient": False,
                    },
                )
                return
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
            grounding, coverage, hallucination, confidence = self._validate_answer(answer, prepared)
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
                    "debug": self._debug_to_dict(prepared.retrieval_debug),
                    "guardrails": prepared.guardrails.model_dump(mode="json") if prepared.guardrails else None,
                    "grounding": grounding.model_dump(mode="json") if grounding else None,
                    "citation_coverage": coverage.model_dump(mode="json") if coverage else None,
                    "hallucination_risk": hallucination.model_dump(mode="json") if hallucination else None,
                    "retrieval_metrics": prepared.retrieval_metrics.model_dump(mode="json") if prepared.retrieval_metrics else None,
                    "context_sufficient": True,
                    "confidence": confidence,
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

    def _retrieve_chunks(
        self,
        db: Session,
        user_id: int,
        request: ChatQueryRequest,
    ) -> tuple[list[SearchResult], RetrievalDebug | None]:
        retrieve_with_debug = getattr(self.retriever_service, "retrieve_with_debug", None)
        if retrieve_with_debug is not None:
            retrieval_result = retrieve_with_debug(
                db=db,
                question=request.question,
                user_id=user_id,
                contract_ids=request.contract_ids,
                top_k=request.top_k,
                search_mode=request.search_mode.value,
                rerank=request.rerank,
            )
            return retrieval_result.results, retrieval_result.debug

        chunks = self.retriever_service.retrieve(
            db=db,
            question=request.question,
            user_id=user_id,
            contract_ids=request.contract_ids,
            top_k=request.top_k,
        )
        return chunks, None

    def _validate_answer(
        self,
        answer: str,
        prepared: RAGResult,
    ) -> tuple[GroundingResult | None, CitationCoverage | None, HallucinationRisk | None, int | None]:
        coverage = (
            self.citation_validator.validate(answer, len(prepared.citations))
            if settings.enable_citation_validation
            else None
        )
        grounding = (
            self.grounding_validator.validate(
                answer,
                prepared.constructed_context,
                len(prepared.citations),
            )
            if settings.enable_grounding_check
            else None
        )
        hallucination = None
        if (
            settings.enable_hallucination_check
            and coverage is not None
            and grounding is not None
            and prepared.retrieval_metrics is not None
        ):
            hallucination = self.hallucination_service.calculate(
                prepared.retrieval_metrics,
                coverage,
                grounding,
            )
        confidence = 100 - hallucination.score if hallucination else grounding.score if grounding else None
        return grounding, coverage, hallucination, confidence

    @staticmethod
    def _insufficient(prepared: RAGResult) -> InsufficientContextResponse:
        return InsufficientContextResponse(
            message="Soruya güvenilir bir cevap üretmek için yeterli ve güvenli context bulunamadı.",
            guardrails=prepared.guardrails,
            retrieval_metrics=prepared.retrieval_metrics,
        )

    @staticmethod
    def _debug_to_dict(debug: RetrievalDebug | None) -> dict | None:
        if debug is None:
            return None
        return {
            "vector_hits": [hit.__dict__ for hit in debug.vector_hits],
            "keyword_hits": [hit.__dict__ for hit in debug.keyword_hits],
            "merged_hits": [hit.__dict__ for hit in debug.merged_hits],
            "reranked_hits": [hit.__dict__ for hit in debug.reranked_hits],
        }
