from types import SimpleNamespace
from unittest.mock import patch

from app.legal_analysis.schemas.analysis import LegalAnalysisResponse
from app.legal_analysis.xai.confidence_builder import ConfidenceBuilder
from app.legal_analysis.xai.evidence_builder import EvidenceBuilder
from app.legal_analysis.xai.retrieval_path_builder import RetrievalPathBuilder
from app.legal_analysis.xai.schemas import ConfidenceLevel
from app.models.contract import Contract
from app.retrieval.base import SearchResult


def analysis_response() -> LegalAnalysisResponse:
    return LegalAnalysisResponse.model_validate(
        {
            "analysis_type": "full",
            "summary": "Fesih hükmü belirsizdir.",
            "risk_score": 70,
            "risk_category": "HIGH",
            "confidence": 0.9,
            "risks": [
                {
                    "title": "Belirsiz fesih",
                    "description": "Bildirim süresi açık değildir.",
                    "severity": "HIGH",
                    "reason": "Uyuşmazlık riski doğurur.",
                    "citation": 1,
                }
            ],
            "missing_clauses": [],
            "ambiguous_clauses": [],
            "one_sided_clauses": [],
            "recommendations": [],
            "citations": [
                {"contract_id": 1, "chunk_id": 1, "chunk_index": 0, "score": 0.9}
            ],
        }
    )


def source_chunks() -> list[SearchResult]:
    return [
        SearchResult(0.9, 1, 1, 0, 1, "Taraflar makul sürede feshedebilir.", {}, vector_score=0.82, rerank_score=0.9),
        SearchResult(0.85, 2, None, 1, 2, "Madde 27 fesih hükümleri.", {"document_type": "LAW", "title": "TBK", "article": "27"}, vector_score=0.8, rerank_score=0.85, source_type="legal", document_id=5),
        SearchResult(0.8, 3, None, 2, 3, "Fesih bildirimi belirli olmalıdır.", {"document_type": "SUPREME_COURT", "title": "Yargıtay 9. HD"}, vector_score=0.75, rerank_score=0.8, source_type="legal", document_id=6),
    ]


def test_confidence_score_uses_source_coverage_and_scores() -> None:
    score, level = ConfidenceBuilder().build(0.9, source_chunks())

    assert 80 <= score <= 100
    assert level is ConfidenceLevel.VERY_HIGH


def test_evidence_and_reasoning_include_contract_law_and_case() -> None:
    evidence, reasoning = EvidenceBuilder().build(analysis_response(), source_chunks())

    assert evidence[0].contract_chunk is not None
    assert evidence[0].law_chunk.article == "27"
    assert evidence[0].case_law_chunk.source_type == "case_law"
    assert "TBK" in reasoning[0].law_basis


def test_retrieval_path_exposes_all_processing_stages() -> None:
    path = RetrievalPathBuilder().build(source_chunks())

    assert [step.stage for step in path] == [
        "Question",
        "Contract Retrieval",
        "Law Retrieval",
        "Case Retrieval",
        "Hybrid Merge",
        "Re-ranking",
        "Gemini",
        "Answer",
    ]


def test_explain_endpoint_returns_transparent_analysis(client, current_user, db) -> None:
    contract = Contract(
        user_id=current_user.id,
        original_filename="contract.pdf",
        stored_filename="contract-xai.pdf",
        storage_key="contracts/contract-xai.pdf",
        mime_type="application/pdf",
        file_size=100,
        status="embedded",
    )
    db.add(contract)
    db.commit()
    response_payload = {
        "analysis": analysis_response().model_dump(mode="json"),
        "confidence_score": 88,
        "confidence_level": "VERY_HIGH",
        "reasoning": [],
        "evidence": [],
        "retrieval_path": [],
        "matched_articles": [],
        "matched_cases": [],
        "used_contract_chunks": [],
        "citations": analysis_response().citations,
    }
    service = SimpleNamespace(explain=lambda **kwargs: response_payload)

    with patch(
        "app.api.v1.endpoints.contracts.ExplainableAnalysisService",
        return_value=service,
    ):
        response = client.post(f"/api/v1/contracts/{contract.id}/analysis/explain")

    assert response.status_code == 200
    assert response.json()["confidence_score"] == 88
    assert response.json()["analysis"]["risk_score"] == 70
