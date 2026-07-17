import logging

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
)
from app.rag.citation_builder import CitationBuilder
from app.rag.multi_source_context_builder import MultiSourceContextBuilder
from app.repositories.contract_repository import ContractRepository
from app.services.llm_service import LLMService
from app.services.multi_source_retriever_service import MultiSourceRetrieverService

logger = logging.getLogger(__name__)


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
    ) -> None:
        self.retriever_service = retriever_service or MultiSourceRetrieverService()
        self.context_builder = context_builder or MultiSourceContextBuilder()
        self.prompt_builder = prompt_builder or AnalysisPromptBuilder()
        self.response_parser = response_parser or AnalysisResponseParser()
        self.citation_builder = citation_builder or CitationBuilder()
        self.llm_service = llm_service or LLMService()

    def analyze(
        self,
        db: Session,
        user_id: int,
        contract_id: int,
        request: LegalAnalysisRequest,
    ) -> LegalAnalysisResponse:
        self._validate_contract(db=db, contract_id=contract_id, user_id=user_id)

        retrieval_result = self.retriever_service.retrieve_with_debug(
            db=db,
            question=self.ANALYSIS_QUERY,
            user_id=user_id,
            contract_ids=[contract_id],
            top_k=settings.rerank_top_n,
            search_mode="hybrid",
            rerank=True,
        )
        if not retrieval_result.results:
            raise BadRequestException(detail="Sözleşme için analiz edilecek kaynak bulunamadı")

        context = self.context_builder.build(retrieval_result.results)
        citations = self.citation_builder.build(retrieval_result.results)
        prompt = self.prompt_builder.build(context=context, citation_count=len(citations))
        raw_response = self.llm_service.generate(prompt)

        try:
            parsed = self.response_parser.parse(raw_response)
        except AnalysisResponseParseError as exc:
            logger.exception("Hukuki analiz yanıtı parse edilemedi")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Analiz modeli geçerli bir yanıt döndürmedi",
            ) from exc

        return LegalAnalysisResponse(
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
        )

    @staticmethod
    def _validate_contract(db: Session, contract_id: int, user_id: int) -> None:
        contract = ContractRepository(db).get_by_id(contract_id)
        if not contract:
            raise NotFoundException(detail="Sözleşme bulunamadı")
        if contract.user_id != user_id:
            raise ForbiddenException(detail="Bu sözleşmeyi analiz etme yetkiniz yok")
        if contract.status != "embedded":
            raise BadRequestException(detail="Sözleşme analiz için henüz hazır değil")
