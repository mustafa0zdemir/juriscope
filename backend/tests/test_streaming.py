from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core.exceptions import LLMUnavailableException
from app.llm.gemini_provider import GeminiProvider
from app.retrieval.base import SearchResult
from app.schemas.chat import ChatQueryRequest
from app.services.rag_service import RAGService


def make_chunk() -> SearchResult:
    return SearchResult(
        score=0.91,
        chunk_id=10,
        contract_id=42,
        chunk_index=0,
        page_number=3,
        text="Fesih koşulları",
        metadata={},
    )


def test_gemini_provider_streams_text_chunks() -> None:
    class FakeModels:
        def generate_content_stream(self, **kwargs):
            assert kwargs["model"] == "gemini-test"
            return [SimpleNamespace(text="İlk "), SimpleNamespace(text="parça")]

    from app.config.settings import settings

    with patch.object(settings, "gemini_api_key", "test-key"), patch.object(
        settings, "gemini_model", "gemini-test"
    ):
        provider = GeminiProvider(client=SimpleNamespace(models=FakeModels()))
        assert list(provider.generate_stream("Prompt")) == ["İlk ", "parça"]


def test_rag_stream_saves_only_completed_assistant_answer() -> None:
    fake_llm = SimpleNamespace(
        model_name="gemini-test",
        generate_stream=lambda prompt: iter(["Tam ", "cevap"]),
    )
    fake_retriever = SimpleNamespace(retrieve=lambda **kwargs: [make_chunk()])
    fake_conversation_service = SimpleNamespace(add_message=Mock())

    with patch(
        "app.services.conversation_service.ConversationService",
        return_value=fake_conversation_service,
    ) as conversation_class:
        events = list(
            RAGService(
                retriever_service=fake_retriever, llm_service=fake_llm
            ).stream_query(
                db=object(),
                user_id=7,
                request=ChatQueryRequest(question="Soru"),
                conversation_id=12,
            )
        )

    assert [event.event for event in events] == ["start", "token", "token", "citations", "done"]
    conversation_class.return_value.add_message.assert_called_once()
    saved = conversation_class.return_value.add_message.call_args.kwargs
    assert saved["content"] == "Tam cevap"
    assert saved["citations"][0]["chunk_id"] == 10


def test_rag_stream_does_not_save_partial_answer_after_provider_error() -> None:
    def failing_stream(prompt):
        yield "Yarım cevap"
        raise LLMUnavailableException(detail="Gemini kapandı")

    fake_llm = SimpleNamespace(model_name="gemini-test", generate_stream=failing_stream)
    fake_retriever = SimpleNamespace(retrieve=lambda **kwargs: [make_chunk()])

    with patch("app.services.conversation_service.ConversationService") as conversation_class:
        events = list(
            RAGService(
                retriever_service=fake_retriever, llm_service=fake_llm
            ).stream_query(
                db=object(),
                user_id=7,
                request=ChatQueryRequest(question="Soru"),
                conversation_id=12,
            )
        )

    assert [event.event for event in events] == ["start", "token", "error"]
    conversation_class.return_value.add_message.assert_not_called()


def test_stream_endpoint_returns_sse_and_conversation_id(client, auth_headers):
    from unittest.mock import patch

    fake_events = [
        SimpleNamespace(event="start", data={"conversation_id": 1}),
        SimpleNamespace(event="token", data={"text": "Cevap"}),
        SimpleNamespace(event="done", data={"conversation_id": 1, "model": "test", "latency_ms": 3}),
    ]
    fake_rag = SimpleNamespace(stream_query=lambda **kwargs: iter(fake_events))

    with patch("app.api.v1.endpoints.chat.RAGService", return_value=fake_rag):
        response = client.post(
            "/api/v1/chat/stream",
            headers=auth_headers,
            json={"question": "Soru"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: token" in response.text
    assert '"text": "Cevap"' in response.text
