import logging
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.legal_analysis.builders.analysis_prompt_builder import AnalysisPromptBuilder
from app.legal_analysis.models.analysis import risk_category_for_score
from app.legal_analysis.parsers.analysis_response_parser import (
    AnalysisResponseParseError,
    AnalysisResponseParser,
)
from app.legal_analysis.schemas.analysis import (
    AnalysisCitation,
    LegalAnalysisRequest,
    LegalAnalysisResponse,
    ParsedAnalysisResponse,
)
from app.rag.citation_builder import CitationBuilder
from app.rag.multi_source_context_builder import MultiSourceContextBuilder
from app.repositories.contract_repository import ContractRepository
from app.services.llm_service import LLMService
from app.services.multi_source_retriever_service import MultiSourceRetrieverService
from app.retrieval.base import SearchResult
from app.trustworthy_rag.schemas import InsufficientContextResponse
from app.trustworthy_rag.services.citation_coverage_validator import CitationCoverageValidator
from app.trustworthy_rag.services.grounding_validator import GroundingValidator
from app.trustworthy_rag.services.hallucination_risk_service import HallucinationRiskService
from app.trustworthy_rag.services.rag_guard_service import RAGGuardService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LegalAnalysisExecution:
    analysis: LegalAnalysisResponse
    retrieved_chunks: list[SearchResult]


class LegalAnalysisService:
    """Tek sözleşme için retrieval destekli hukuki analiz akışını orkestre eder."""

    ANALYSIS_QUERY = (
        "Sözleşmenin taraf yükümlülükleri, fesih, sorumluluk, gizlilik, KVKK, "
        "mücbir sebep, uyuşmazlık çözümü ve yetkili mahkeme hükümlerini; hukuki "
        "riskleri, eksik maddeleri, belirsiz ifadeleri ve tek taraflı şartları incele."
    )

    def __init__(
        self,
        retriever_service: MultiSourceRetrieverService | None = None,
        context_builder: MultiSourceContextBuilder | None = None,
        prompt_builder: AnalysisPromptBuilder | None = None,
        response_parser: AnalysisResponseParser | None = None,
        citation_builder: CitationBuilder | None = None,
        llm_service: LLMService | None = None,
        guard_service: RAGGuardService | None = None,
        grounding_validator: GroundingValidator | None = None,
        citation_validator: CitationCoverageValidator | None = None,
        hallucination_service: HallucinationRiskService | None = None,
    ) -> None:
        self.retriever_service = retriever_service or MultiSourceRetrieverService()
        self.context_builder = context_builder or MultiSourceContextBuilder()
        self.prompt_builder = prompt_builder or AnalysisPromptBuilder()
        self.response_parser = response_parser or AnalysisResponseParser()
        self.citation_builder = citation_builder or CitationBuilder()
        self.llm_service = llm_service or LLMService()
        self.guard_service = guard_service or RAGGuardService()
        self.grounding_validator = grounding_validator or GroundingValidator()
        self.citation_validator = citation_validator or CitationCoverageValidator()
        self.hallucination_service = hallucination_service or HallucinationRiskService()

    def analyze(
        self,
        db: Session,
        user_id: int,
        contract_id: int,
        request: LegalAnalysisRequest,
    ) -> LegalAnalysisResponse | InsufficientContextResponse:
        result = self.analyze_with_sources(db, user_id, contract_id, request)
        return result.analysis if isinstance(result, LegalAnalysisExecution) else result

    def analyze_with_sources(
        self,
        db: Session,
        user_id: int,
        contract_id: int,
        request: LegalAnalysisRequest,
    ) -> LegalAnalysisExecution | InsufficientContextResponse:
        self._validate_contract(db=db, contract_id=contract_id, user_id=user_id)

        retrieval_result = self.retriever_service.retrieve_with_debug(
            db=db,
            question=self.ANALYSIS_QUERY,
            user_id=user_id,
            contract_ids=[contract_id],
            top_k=settings.analysis_top_k,
            search_mode="hybrid",
            rerank=settings.analysis_rerank_enabled,
        )
        context = self.context_builder.build(retrieval_result.results)
        citations = self.citation_builder.build(retrieval_result.results)
        guardrails, retrieval_metrics = self.guard_service.evaluate(
            question=self.ANALYSIS_QUERY,
            chunks=retrieval_result.results,
            context=context,
            search_mode="hybrid",
        )
        if not guardrails.passed:
            return InsufficientContextResponse(
                message="Hukuki analiz için yeterli ve güvenli context bulunamadı.",
                guardrails=guardrails,
                retrieval_metrics=retrieval_metrics,
            )
        prompt = self.prompt_builder.build(context=context, citation_count=len(citations))
        generate_json = getattr(self.llm_service, "generate_json", None)
        raw_response = (
            generate_json(prompt, ParsedAnalysisResponse)
            if generate_json
            else self.llm_service.generate(prompt)
        )
        coverage = (
            self.citation_validator.validate(raw_response, len(citations))
            if settings.enable_citation_validation
            else None
        )
        grounding = (
            self.grounding_validator.validate(raw_response, context, len(citations))
            if settings.enable_grounding_check
            else None
        )
        hallucination = (
            self.hallucination_service.calculate(retrieval_metrics, coverage, grounding)
            if settings.enable_hallucination_check and coverage and grounding
            else None
        )

        try:
            parsed = self.response_parser.parse(raw_response)
        except AnalysisResponseParseError as exc:
            logger.exception("Hukuki analiz yanıtı parse edilemedi")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Analiz modeli geçerli bir yanıt döndürmedi",
            ) from exc

        analysis = LegalAnalysisResponse(
            analysis_type=request.analysis_type,
            summary=parsed.summary,
            risk_score=parsed.risk_score,
            risk_category=risk_category_for_score(parsed.risk_score),
            confidence=parsed.confidence,
            risks=parsed.risks,
            missing_clauses=parsed.missing_clauses,
            ambiguous_clauses=parsed.ambiguous_clauses,
            one_sided_clauses=parsed.one_sided_clauses,
            recommendations=parsed.recommendations,
            citations=[AnalysisCitation.model_validate(citation.to_dict()) for citation in citations],
            guardrails=guardrails,
            grounding=grounding,
            citation_coverage=coverage,
            hallucination_risk=hallucination,
            retrieval_metrics=retrieval_metrics,
            context_sufficient=True,
        )
        return LegalAnalysisExecution(analysis=analysis, retrieved_chunks=retrieval_result.results)

    @staticmethod
    def _validate_contract(db: Session, contract_id: int, user_id: int) -> None:
        contract = ContractRepository(db).get_by_id(contract_id)
        if not contract:
            raise NotFoundException(detail="Sözleşme bulunamadı")
        if contract.user_id != user_id:
            raise ForbiddenException(detail="Bu sözleşmeyi analiz etme yetkiniz yok")
        if contract.status != "embedded":
            raise BadRequestException(detail="Sözleşme analiz için henüz hazır değil")
