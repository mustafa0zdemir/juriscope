from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.exceptions import ForbiddenException
from app.rag.citation_builder import CitationBuilder
from app.rag.context_builder import ContextBuilder
from app.rag.prompt_builder import PromptBuilder
from app.retrieval.base import SearchResult
from app.schemas.chat import ChatQueryRequest
from app.services.rag_service import RAGService
from app.services.retriever_service import RetrieverService


def make_chunk(index: int = 0, text: str = "Sözleşme metni") -> SearchResult:
    return SearchResult(
        score=0.9 - index / 10,
        chunk_id=index + 10,
        contract_id=42,
        chunk_index=index,
        page_number=index + 1,
        text=text,
        metadata={"language": "tr"},
    )


def test_context_builder_respects_limit_and_separates_chunks() -> None:
    context = ContextBuilder(max_context_chars=220).build(
        [make_chunk(text="Birinci metin"), make_chunk(1, "İkinci metin")]
    )

    assert len(context) <= 220
    assert "---" in context
    assert "contract_id=42" in context


def test_prompt_builder_contains_required_sections() -> None:
    prompt = PromptBuilder().build("Fesih süresi nedir?", "Kaynak metin", ["[Kaynak 1]"])

    assert "SİSTEM ROLÜ" in prompt
    assert "Fesih süresi nedir?" in prompt
    assert "Kaynak metin" in prompt
    assert "CEVAP KURALLARI" in prompt
    assert "KAYNAK GÖSTERME TALİMATI" in prompt


def test_citation_builder_maps_required_fields() -> None:
    citation = CitationBuilder().build([make_chunk()])[0]

    assert citation.to_dict() == {
        "contract_id": 42,
        "chunk_id": 10,
        "chunk_index": 0,
        "page_number": 1,
        "score": 0.9,
    }


def test_retriever_service_preserves_top_k_and_authorizes_contracts() -> None:
    fake_retriever = SimpleNamespace(search=lambda **kwargs: kwargs)
    fake_contract = SimpleNamespace(id=42, user_id=7)
    fake_repository = SimpleNamespace(get_by_id=lambda contract_id: fake_contract)
    fake_embedding = SimpleNamespace(embed_text=lambda question: [0.1, 0.2])

    with (
        patch("app.services.retriever_service.ContractRepository", return_value=fake_repository),
        patch(
            "app.services.retriever_service.SentenceTransformerProvider.get_instance",
            return_value=fake_embedding,
        ),
    ):
        result = RetrieverService(fake_retriever).retrieve(
            db=object(), question="Soru", user_id=7, contract_ids=[42], top_k=3
        )

    assert result["top_k"] == 3
    assert result["contract_ids"] == [42]


def test_retriever_service_rejects_other_users_contract() -> None:
    fake_repository = SimpleNamespace(
        get_by_id=lambda contract_id: SimpleNamespace(id=42, user_id=99)
    )

    with patch(
        "app.services.retriever_service.ContractRepository", return_value=fake_repository
    ):
        with pytest.raises(ForbiddenException):
            RetrieverService(SimpleNamespace()).retrieve(
                db=object(), question="Soru", user_id=7, contract_ids=[42]
            )


def test_rag_service_prepares_prompt_without_calling_llm() -> None:
    fake_retriever = SimpleNamespace(retrieve=lambda **kwargs: [make_chunk()])
    service = RAGService(retriever_service=fake_retriever)

    result = service.prepare_query(
        db=object(), user_id=7, request=ChatQueryRequest(question="Fesih süresi?")
    )

    assert result.question == "Fesih süresi?"
    assert result.retrieved_chunks[0].chunk_id == 10
    assert "Fesih süresi?" in result.constructed_prompt
    assert result.citations[0].contract_id == 42


def test_prompt_preview_endpoint_is_registered() -> None:
    from app.api.v1.endpoints.chat import router

    paths = {route.path for route in router.routes}

    assert "/chat/query" in paths
    assert "/chat/prompt-preview" in paths
