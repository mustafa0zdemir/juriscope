import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.exceptions import ForbiddenException
from app.legal_analysis.builders.analysis_prompt_builder import AnalysisPromptBuilder
from app.legal_analysis.models.analysis import RiskCategory, risk_category_for_score
from app.legal_analysis.parsers.analysis_response_parser import AnalysisResponseParser
from app.legal_analysis.schemas.analysis import LegalAnalysisRequest, LegalAnalysisResponse
from app.legal_analysis.services.legal_analysis_service import LegalAnalysisService
from app.models.contract import Contract
from app.rag.citation_builder import Citation
from app.retrieval.base import SearchResult
from app.retrieval.hybrid_retriever import HybridSearchResult, RetrievalDebug


def make_chunk() -> SearchResult:
    return SearchResult(
        score=0.91,
        chunk_id=10,
        contract_id=42,
        chunk_index=0,
        page_number=3,
        text="Fesih halinde bildirim süresi makul süre olarak belirlenmiştir.",
        metadata={},
    )


def make_analysis_json() -> str:
    return json.dumps(
        {
            "summary": "Sözleşmede fesih süresi belirsizdir.",
            "risk_score": 82,
            "confidence": 0.91,
            "risks": [
                {
                    "title": "Belirsiz fesih süresi",
                    "description": "Makul süre ifadesi net değildir.",
                    "severity": "HIGH",
                    "reason": "Taraflar arasında uyuşmazlık yaratabilir.",
                    "citation": 1,
                }
            ],
            "missing_clauses": [
                {"title": "KVKK", "description": "Veri koruma hükmü bulunamadı.", "citation": None}
            ],
            "ambiguous_clauses": [
                {"title": "Makul süre", "description": "Süre tanımlanmamış.", "citation": 1}
            ],
            "one_sided_clauses": [],
            "recommendations": [
                {
                    "title": "Süreyi netleştirin",
                    "description": "Fesih bildirim süresini gün cinsinden yazın.",
                    "related_risk": "Belirsiz fesih süresi",
                }
            ],
            "citations": [1],
        }
    )


def make_response() -> LegalAnalysisResponse:
    return LegalAnalysisResponse.model_validate(
        {
            **json.loads(make_analysis_json()),
            "analysis_type": "full",
            "risk_category": "CRITICAL",
            "citations": [
                {
                    "contract_id": 42,
                    "chunk_id": 10,
                    "chunk_index": 0,
                    "page_number": 3,
                    "score": 0.91,
                }
            ],
        }
    )


def test_analysis_prompt_requires_json_and_citation_rules() -> None:
    prompt = AnalysisPromptBuilder().build("[Kaynak 1]\nMetin", citation_count=1)

    assert "yalnızca geçerli JSON döndür" in prompt
    assert "Kaynak numaraları 1 ile 1 arasındadır" in prompt
    assert "KVKK" in prompt


def test_analysis_response_parser_accepts_json_code_fence() -> None:
    parsed = AnalysisResponseParser().parse(f"```json\n{make_analysis_json()}\n```")

    assert parsed.risk_score == 82
    assert parsed.risks[0].citation == 1
    assert parsed.missing_clauses[0].title == "KVKK"


def test_analysis_response_parser_extracts_json_from_model_preamble() -> None:
    parsed = AnalysisResponseParser().parse(f"Analiz sonucu aşağıdadır:\n{make_analysis_json()}\nTamamlandı.")

    assert parsed.risk_score == 82


@pytest.mark.parametrize(
    ("score", "category"),
    [(0, RiskCategory.LOW), (25, RiskCategory.MEDIUM), (50, RiskCategory.HIGH), (75, RiskCategory.CRITICAL)],
)
def test_risk_score_categories(score: int, category: RiskCategory) -> None:
    assert risk_category_for_score(score) is category


def test_legal_analysis_uses_authorized_retrieval_gemini_and_citations() -> None:
    chunk = make_chunk()
    captured = {}
    fake_retriever = SimpleNamespace(
        retrieve_with_debug=lambda **kwargs: captured.update(kwargs)
        or HybridSearchResult([chunk], RetrievalDebug([], [], [chunk]))
    )
    fake_llm = SimpleNamespace(
        generate_json=lambda prompt, schema: captured.update(
            {"response_schema": schema, "prompt": prompt}
        ) or make_analysis_json()
    )
    contract = SimpleNamespace(id=42, user_id=7, status="embedded")

    with patch(
        "app.legal_analysis.services.legal_analysis_service.ContractRepository",
        return_value=SimpleNamespace(get_by_id=lambda contract_id: contract),
    ):
        result = LegalAnalysisService(
            retriever_service=fake_retriever,
            llm_service=fake_llm,
        ).analyze(
            db=object(),
            user_id=7,
            contract_id=42,
            request=LegalAnalysisRequest(),
        )

    assert captured["contract_ids"] == [42]
    assert captured["search_mode"] == "hybrid"
    assert captured["rerank"] is False
    assert captured["top_k"] == 6
    assert captured["response_schema"].__name__ == "ParsedAnalysisResponse"
    assert "TARAFLARIN DENGELİ DEĞERLENDİRİLMESİ" in captured["prompt"]
    assert result.risk_category is RiskCategory.CRITICAL
    assert [citation.model_dump(exclude_defaults=True, exclude_none=True) for citation in result.citations] == [
        Citation(contract_id=42, chunk_id=10, chunk_index=0, page_number=3, score=0.91).to_dict()
    ]


def test_legal_analysis_rejects_another_users_contract() -> None:
    contract = SimpleNamespace(id=42, user_id=99, status="embedded")
    with patch(
        "app.legal_analysis.services.legal_analysis_service.ContractRepository",
        return_value=SimpleNamespace(get_by_id=lambda contract_id: contract),
    ):
        with pytest.raises(ForbiddenException):
            LegalAnalysisService().analyze(
                db=object(),
                user_id=7,
                contract_id=42,
                request=LegalAnalysisRequest(),
            )


def test_analysis_endpoint_returns_generated_analysis(client, current_user, db) -> None:
    contract = Contract(
        user_id=current_user.id,
        original_filename="sözleşme.pdf",
        stored_filename="contract.pdf",
        storage_key="contracts/contract.pdf",
        mime_type="application/pdf",
        file_size=100,
        status="embedded",
    )
    db.add(contract)
    db.commit()

    fake_service = SimpleNamespace(analyze=lambda **kwargs: make_response())
    with patch(
        "app.api.v1.endpoints.contracts.LegalAnalysisService",
        return_value=fake_service,
    ):
        response = client.post(f"/api/v1/contracts/{contract.id}/analyze", json={"analysis_type": "full"})

    assert response.status_code == 200
    assert response.json()["risk_score"] == 82
    assert response.json()["risks"][0]["severity"] == "HIGH"
