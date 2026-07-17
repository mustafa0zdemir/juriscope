import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.api.v1.endpoints.chat import _debug_to_response
from app.config.settings import settings
from app.reranking.providers.base_provider import RerankTimeoutError
from app.reranking.providers.cross_encoder_provider import CrossEncoderProvider
from app.reranking.rerank_service import ReRankService
from app.retrieval.base import SearchResult
from app.retrieval.hybrid_retriever import HybridSearchResult, RetrievalDebug
from app.services.retriever_service import RetrieverService


def make_chunk(chunk_id: int, score: float) -> SearchResult:
    return SearchResult(
        score=score,
        chunk_id=chunk_id,
        contract_id=10,
        chunk_index=chunk_id,
        page_number=1,
        text=f"Madde {chunk_id}",
        metadata={},
        hybrid_score=score,
    )


def test_cross_encoder_provider_uses_configured_model_and_cpu() -> None:
    model = Mock()
    model.predict.return_value = [0.4]
    with patch.object(settings, "rerank_model", "test-reranker"):
        provider = CrossEncoderProvider(model=model)

    assert provider.model_name == "test-reranker"
    assert provider.score("soru", ["metin"]) == [0.4]
    model.predict.assert_called_once_with([("soru", "metin")], show_progress_bar=False)


def test_cross_encoder_provider_is_loaded_once() -> None:
    CrossEncoderProvider.reset_instance()
    model = Mock()
    with patch.object(CrossEncoderProvider, "_load_model", return_value=model) as load_model:
        first = CrossEncoderProvider.get_instance()
        second = CrossEncoderProvider.get_instance()

    assert first is second
    load_model.assert_called_once()
    CrossEncoderProvider.reset_instance()


def test_cross_encoder_provider_handles_timeout() -> None:
    model = SimpleNamespace(
        predict=lambda pairs, show_progress_bar: (time.sleep(0.05), [0.1])[1]
    )
    provider = CrossEncoderProvider(model=model, timeout_seconds=0.01)

    with pytest.raises(RerankTimeoutError):
        provider.score("soru", ["metin"])


def test_rerank_service_orders_results_and_applies_top_n() -> None:
    provider = SimpleNamespace(score=lambda question, passages: [0.2, 0.9, 0.5])
    result = ReRankService(provider=provider).rerank(
        question="bildirim süresi",
        chunks=[make_chunk(1, 0.8), make_chunk(2, 0.7), make_chunk(3, 0.6)],
        top_n=2,
    )

    assert [chunk.chunk_id for chunk in result] == [2, 3]
    assert [chunk.final_rank for chunk in result] == [1, 2]
    assert [chunk.rerank_score for chunk in result] == [0.9, 0.5]
    assert result[0].hybrid_score == 0.7


def test_rerank_service_falls_back_to_hybrid_order_after_provider_error() -> None:
    provider = SimpleNamespace(score=lambda question, passages: (_ for _ in ()).throw(RuntimeError()))
    result = ReRankService(provider=provider).rerank(
        question="soru",
        chunks=[make_chunk(1, 0.8), make_chunk(2, 0.7)],
        top_n=2,
    )

    assert [chunk.chunk_id for chunk in result] == [1, 2]
    assert [chunk.rerank_score for chunk in result] == [None, None]


def test_retriever_service_reranks_authorized_hybrid_candidates() -> None:
    captured = {}
    candidates = [make_chunk(1, 0.8), make_chunk(2, 0.7)]
    hybrid = SimpleNamespace(
        search=lambda **kwargs: captured.update(kwargs)
        or HybridSearchResult(candidates, RetrievalDebug([], [], candidates))
    )
    rerank_service = SimpleNamespace(
        rerank=lambda **kwargs: [make_chunk(2, 0.7)]
    )
    repository = SimpleNamespace(
        get_by_id=lambda contract_id: SimpleNamespace(id=contract_id, user_id=7)
    )
    embedding = SimpleNamespace(embed_text=lambda question: [0.1, 0.2])

    with (
        patch("app.services.retriever_service.ContractRepository", return_value=repository),
        patch(
            "app.services.retriever_service.SentenceTransformerProvider.get_instance",
            return_value=embedding,
        ),
        patch.object(settings, "rerank_enabled", True),
        patch.object(settings, "rerank_input_limit", 20),
        patch.object(settings, "rerank_top_n", 5),
    ):
        result = RetrieverService(hybrid, rerank_service).retrieve_with_debug(
            db=object(),
            question="madde 17",
            user_id=7,
            contract_ids=[10],
            top_k=5,
        )

    assert captured["contract_ids"] == [10]
    assert captured["top_k"] == 20
    assert [chunk.chunk_id for chunk in result.results] == [2]
    assert [chunk.chunk_id for chunk in result.debug.reranked_hits] == [2]


def test_debug_response_includes_rerank_scores_and_final_rank() -> None:
    reranked = make_chunk(2, 0.7)
    reranked.rerank_score = 0.95
    reranked.final_rank = 1
    debug = RetrievalDebug(
        vector_hits=[make_chunk(1, 0.8)],
        keyword_hits=[make_chunk(2, 0.7)],
        merged_hits=[reranked],
        reranked_hits=[reranked],
    )

    response = _debug_to_response(debug)

    assert response is not None
    assert response.reranked_hits[0].rerank_score == 0.95
    assert response.reranked_hits[0].final_rank == 1
