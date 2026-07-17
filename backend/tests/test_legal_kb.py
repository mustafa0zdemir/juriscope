from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import BackgroundTasks, UploadFile

from app.config.settings import settings
from app.legal_kb.ingestion.legal_ingestion_service import (
    LegalIngestionService,
    process_legal_document_task,
)
from app.legal_kb.models.legal_citation import LegalCitation
from app.legal_kb.models.legal_document import LegalDocument, LegalDocumentType
from app.legal_kb.providers.legal_qdrant_retriever import LegalQdrantRetriever
from app.legal_kb.services.legal_retriever import LegalRetriever
from app.rag.citation_builder import CitationBuilder
from app.rag.multi_source_context_builder import MultiSourceContextBuilder
from app.retrieval.base import SearchResult
from app.retrieval.hybrid_retriever import HybridSearchResult, RetrievalDebug
from app.services.multi_source_retriever_service import MultiSourceRetrieverService


def make_legal_result(chunk_id: int = 20, score: float = 0.8) -> SearchResult:
    return SearchResult(
        score=score,
        chunk_id=chunk_id,
        contract_id=None,
        chunk_index=0,
        page_number=2,
        text="4857 sayılı İş Kanunu Madde 17 bildirim süresini düzenler.",
        metadata={
            "document_type": "LAW",
            "title": "İş Kanunu",
            "official_number": "4857",
            "article": "17",
            "publication_date": "2003-06-10",
            "court": None,
            "decision_number": None,
        },
        source_type="legal",
        document_id=5,
    )


def make_contract_result() -> SearchResult:
    return SearchResult(
        score=0.7,
        chunk_id=10,
        contract_id=42,
        chunk_index=0,
        page_number=1,
        text="Fesih bildirimi makul sürede yapılır.",
        metadata={},
    )


def test_non_admin_cannot_access_legal_management(client) -> None:
    response = client.get("/api/v1/legal")

    assert response.status_code == 403


def test_admin_can_list_legal_documents(client, current_user, db) -> None:
    current_user.is_admin = True
    db.commit()
    document = LegalDocument(
        title="İş Kanunu",
        document_type=LegalDocumentType.LAW,
        source="Resmî Gazete",
        official_number="4857",
        publication_date=date(2003, 6, 10),
        original_filename="is-kanunu.pdf",
        storage_key="legal/law/is-kanunu.pdf",
        mime_type="application/pdf",
        file_size=100,
        status="embedded",
    )
    db.add(document)
    db.commit()

    response = client.get("/api/v1/legal")

    assert response.status_code == 200
    assert response.json()["items"][0]["official_number"] == "4857"


def test_legal_upload_service_stores_file_and_schedules_ingestion(db) -> None:
    storage = SimpleNamespace(upload=Mock())
    background_tasks = BackgroundTasks()
    upload = UploadFile(filename="kanun.pdf", file=__import__("io").BytesIO(b"pdf-content"))

    document = __import__("asyncio").run(
        LegalIngestionService().upload(
            db=db,
            file=upload,
            title="Test Kanunu",
            document_type=LegalDocumentType.LAW,
            source="Resmî Gazete",
            official_number="9999",
            publication_date=date(2026, 1, 1),
            background_tasks=background_tasks,
            storage=storage,
        )
    )

    storage.upload.assert_called_once()
    assert document.status == "uploaded"
    assert len(background_tasks.tasks) == 1


def test_legal_ingestion_reuses_parser_chunking_embedding_and_qdrant() -> None:
    document = SimpleNamespace(
        id=5,
        title="İş Kanunu",
        document_type=LegalDocumentType.LAW,
        source="Resmî Gazete",
        official_number="4857",
        publication_date=date(2003, 6, 10),
        original_filename="kanun.pdf",
        storage_key="legal/law/kanun.pdf",
    )
    legal_chunks = [
        SimpleNamespace(
            id=20,
            document_id=5,
            chunk_index=0,
            page_number=None,
            text="Madde 17 bildirim süresi",
            metadata_={"document_id": 5},
        )
    ]
    document_repository = SimpleNamespace(
        get_by_id=lambda document_id: document,
        update_status=Mock(side_effect=lambda item, status: setattr(item, "status", status) or item),
    )
    chunk_repository = SimpleNamespace(
        create_bulk=Mock(return_value=legal_chunks),
        mark_embedded=Mock(),
    )
    qdrant = SimpleNamespace(upsert_vectors=Mock())
    fake_db = SimpleNamespace(close=Mock())

    with (
        patch("app.legal_kb.ingestion.legal_ingestion_service.SessionLocal", return_value=fake_db),
        patch(
            "app.legal_kb.ingestion.legal_ingestion_service.LegalDocumentRepository",
            return_value=document_repository,
        ),
        patch(
            "app.legal_kb.ingestion.legal_ingestion_service.LegalChunkRepository",
            return_value=chunk_repository,
        ),
        patch("app.legal_kb.ingestion.legal_ingestion_service.MinioProvider"),
        patch(
            "app.legal_kb.ingestion.legal_ingestion_service.StorageService",
            return_value=SimpleNamespace(download=lambda key: b"content"),
        ),
        patch(
            "app.legal_kb.ingestion.legal_ingestion_service.get_parser",
            return_value=SimpleNamespace(parse=lambda content: ("Madde 17 bildirim süresi", 1, "PDF")),
        ),
        patch(
            "app.legal_kb.ingestion.legal_ingestion_service.SentenceTransformerProvider.get_instance",
            return_value=SimpleNamespace(embed_text=lambda text: [0.1, 0.2]),
        ),
        patch("app.legal_kb.ingestion.legal_ingestion_service.QdrantService", return_value=qdrant),
    ):
        process_legal_document_task(5)

    chunk_repository.create_bulk.assert_called_once()
    chunk_repository.mark_embedded.assert_called_once_with(legal_chunks)
    qdrant.upsert_vectors.assert_called_once()
    assert document.status == "embedded"


def test_legal_qdrant_retriever_applies_collection_and_type_filter() -> None:
    captured = {}
    client = SimpleNamespace(search=lambda **kwargs: captured.update(kwargs) or [])

    LegalQdrantRetriever(client).search(
        query_vector=[0.1],
        top_k=3,
        document_types=[LegalDocumentType.SUPREME_COURT],
    )

    assert captured["collection_name"] == settings.legal_collection
    assert captured["limit"] == 3
    assert captured["query_filter"] is not None


def test_legal_retriever_merges_and_reranks_results() -> None:
    vector = SimpleNamespace(search=lambda **kwargs: [make_legal_result(20, 0.8)])
    bm25 = SimpleNamespace(search=lambda **kwargs: [make_legal_result(21, 4.0)])
    reranker = SimpleNamespace(rerank=lambda question, chunks, top_n: [chunks[-1]])
    embedding = SimpleNamespace(embed_text=lambda question: [0.1])

    with (
        patch(
            "app.legal_kb.services.legal_retriever.SentenceTransformerProvider.get_instance",
            return_value=embedding,
        ),
        patch.object(settings, "enable_legal_search", True),
        patch.object(settings, "rerank_enabled", True),
    ):
        results = LegalRetriever(vector, bm25, reranker).retrieve(
            db=object(), question="bildirim süresi", top_k=2
        )

    assert len(results) == 1
    assert results[0].source_type == "legal"


def test_multi_source_retrieval_combines_contract_and_legal_results() -> None:
    contract = make_contract_result()
    legal = make_legal_result()
    contract_retriever = SimpleNamespace(
        retrieve_with_debug=lambda **kwargs: HybridSearchResult(
            [contract], RetrievalDebug([], [], [contract])
        )
    )
    legal_retriever = SimpleNamespace(retrieve=lambda **kwargs: [legal])
    reranker = SimpleNamespace(rerank=lambda question, chunks, top_n: chunks[:top_n])

    with patch.object(settings, "enable_multi_source_rag", True), patch.object(
        settings, "rerank_enabled", True
    ):
        result = MultiSourceRetrieverService(
            contract_retriever, legal_retriever, reranker
        ).retrieve_with_debug(db=object(), question="fesih", user_id=7, top_k=2)

    assert {item.source_type for item in result.results} == {"contract", "legal"}


def test_multi_source_context_and_legal_citation_preserve_source_identity() -> None:
    contract = make_contract_result()
    legal = make_legal_result()

    context = MultiSourceContextBuilder().build([contract, legal])
    citations = CitationBuilder().build([contract, legal])

    assert "KULLANICI SÖZLEŞMESİ" in context
    assert "KANUNLAR" in context
    assert isinstance(citations[1], LegalCitation)
    assert citations[1].official_number == "4857"
