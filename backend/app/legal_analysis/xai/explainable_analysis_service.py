from sqlalchemy.orm import Session

from app.legal_analysis.schemas.analysis import LegalAnalysisRequest
from app.legal_analysis.services.legal_analysis_service import LegalAnalysisService
from app.legal_analysis.xai.confidence_builder import ConfidenceBuilder
from app.legal_analysis.xai.evidence_builder import EvidenceBuilder
from app.legal_analysis.xai.retrieval_path_builder import RetrievalPathBuilder
from app.legal_analysis.xai.schemas import ExplainableAnalysisResponse


class ExplainableAnalysisService:
    def __init__(
        self,
        analysis_service: LegalAnalysisService | None = None,
        confidence_builder: ConfidenceBuilder | None = None,
        evidence_builder: EvidenceBuilder | None = None,
        retrieval_path_builder: RetrievalPathBuilder | None = None,
    ) -> None:
        self.analysis_service = analysis_service or LegalAnalysisService()
        self.confidence_builder = confidence_builder or ConfidenceBuilder()
        self.evidence_builder = evidence_builder or EvidenceBuilder()
        self.retrieval_path_builder = retrieval_path_builder or RetrievalPathBuilder()

    def explain(self, db: Session, user_id: int, contract_id: int) -> ExplainableAnalysisResponse:
        execution = self.analysis_service.analyze_with_sources(
            db=db,
            user_id=user_id,
            contract_id=contract_id,
            request=LegalAnalysisRequest(),
        )
        confidence_score, confidence_level = self.confidence_builder.build(
            execution.analysis.confidence,
            execution.retrieved_chunks,
        )
        evidence, reasoning = self.evidence_builder.build(
            execution.analysis,
            execution.retrieved_chunks,
        )
        contract_chunks, articles, cases = self.evidence_builder.sources(execution.retrieved_chunks)
        return ExplainableAnalysisResponse(
            analysis=execution.analysis,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            reasoning=reasoning,
            evidence=evidence,
            retrieval_path=self.retrieval_path_builder.build(execution.retrieved_chunks),
            matched_articles=articles,
            matched_cases=cases,
            used_contract_chunks=contract_chunks,
            citations=execution.analysis.citations,
        )
