from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.config.settings import settings
from app.core.exceptions import ForbiddenException
from app.retrieval.base import SearchResult
from app.retrieval.hybrid_retriever import HybridRetriever, HybridSearchResult, RetrievalDebug
from app.schemas.chat import ChatQueryRequest
from app.services.rag_service import RAGService
from app.services.bm25_service import BM25Service
from app.services.retriever_service import RetrieverService


def make_result(chunk_id: int, score: float, text: str = "madde metni") -> SearchResult:
    return SearchResult(
        score=score,
        chunk_id=chunk_id,
        contract_id=1,
        chunk_index=chunk_id,
        page_number=1,
        text=text,
        metadata={},
    )


def test_bm25_returns_keyword_matches_from_authorized_chunks() -> None:
    chunks = [
        SimpleNamespace(
            id=1,
            contract_id=10,
            chunk_index=0,
            page_number=1,
            text="4857 sayılı İş Kanunu madde 17 bildirim süresi",
            metadata_={},
        ),
        SimpleNamespace(
            id=2,
            contract_id=10,
            chunk_index=1,
            page_number=2,
            text="Tarafların genel yükümlülükleri açıklanmıştır",
            metadata_={},
        ),
    ]
    repository = SimpleNamespace(list_by_contract_ids=lambda contract_ids: chunks)

    results = BM25Service(repository).search(
        db=object(), question="4857 madde 17", contract_ids=[10], top_k=5
    )

    assert [result.chunk_id for result in results] == [1]
    assert results[0].keyword_score is not None


def test_hybrid_merge_normalizes_and_removes_duplicates() -> None:
    vector_hits = [make_result(1, 0.9), make_result(2, 0.7)]
    keyword_hits = [make_result(1, 8.0), make_result(3, 4.0)]

    merged = HybridRetriever.merge(vector_hits, keyword_hits)

    assert [hit.chunk_id for hit in merged].count(1) == 1
    assert {hit.chunk_id for hit in merged} == {1, 2, 3}
    assert all(0 <= hit.score <= 1 for hit in merged)
    assert next(hit for hit in merged if hit.chunk_id == 1).vector_score == 0.9


def test_hybrid_retriever_applies_top_k_after_merge() -> None:
    vector_retriever = SimpleNamespace(search=lambda **kwargs: [make_result(1, 0.9), make_result(2, 0.7)])
    bm25_service = SimpleNamespace(search=lambda **kwargs: [make_result(3, 5.0), make_result(4, 4.0)])
    retriever = HybridRetriever(vector_retriever=vector_retriever, bm25_service=bm25_service)

    result = retriever.search(
        db=object(),
        question="madde",
        contract_ids=[1],
        query_vector=[0.1],
        search_mode="hybrid",
        top_k=2,
    )

    assert len(result.results) == 2
    assert len(result.debug.merged_hits) == 4


def test_keyword_mode_does_not_create_embedding_and_keeps_authorization() -> None:
    captured = {}
    fake_hybrid = SimpleNamespace(
        search=lambda **kwargs: captured.update(kwargs)
        or HybridSearchResult([], RetrievalDebug([], [], []))
    )
    repository = SimpleNamespace(
        get_by_id=lambda contract_id: SimpleNamespace(id=contract_id, user_id=7)
    )

    with (
        patch("app.services.retriever_service.ContractRepository", return_value=repository),
        patch("app.services.retriever_service.SentenceTransformerProvider.get_instance") as embedding,
    ):
        RetrieverService(fake_hybrid).retrieve_with_debug(
            db=object(),
            question="4857",
            user_id=7,
            contract_ids=[10],
            search_mode="keyword",
        )

    embedding.assert_not_called()
    assert captured["contract_ids"] == [10]
    assert captured["query_vector"] is None


def test_retriever_rejects_unauthorized_contract_for_bm25() -> None:
    fake_hybrid = SimpleNamespace()
    repository = SimpleNamespace(
        get_by_id=lambda contract_id: SimpleNamespace(id=contract_id, user_id=99)
    )

    with patch("app.services.retriever_service.ContractRepository", return_value=repository):
        with pytest.raises(ForbiddenException):
            RetrieverService(fake_hybrid).retrieve_with_debug(
                db=object(),
                question="gizli madde",
                user_id=7,
                contract_ids=[10],
                search_mode="keyword",
            )


def test_debug_setting_is_configurable() -> None:
    debug = RetrievalDebug(
        vector_hits=[make_result(1, 0.9)],
        keyword_hits=[make_result(2, 3.0)],
        merged_hits=[make_result(1, 1.0), make_result(2, 0.8)],
    )
    fake_retriever = SimpleNamespace(
        retrieve_with_debug=lambda **kwargs: HybridSearchResult([make_result(1, 1.0)], debug)
    )

    with patch.object(settings, "enable_debug_search", True):
        result = RAGService(retriever_service=fake_retriever).prepare_query(
            db=object(),
            user_id=7,
            request=ChatQueryRequest(question="4857 madde 17"),
        )

    assert result.retrieval_debug == debug
