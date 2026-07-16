import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.conversation import Conversation
from app.models.user import User


@pytest.fixture
def other_user(db: Session):
    user = User(
        username="otheruser",
        email="other@example.com",
        hashed_password="hashed_password",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_conversation(client, auth_headers):
    response = client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "Test Sohbet"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Test Sohbet"
    assert "id" in data


def test_list_conversations(client, auth_headers):
    # Sohbet oluştur
    client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "Test Sohbet"},
    )

    response = client.get("/api/v1/conversations", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Test Sohbet"


def test_get_conversation(client, auth_headers):
    create_response = client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "Test Sohbet"},
    )
    conversation_id = create_response.json()["id"]

    response = client.get(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == conversation_id


def test_conversation_not_found(client, auth_headers):
    response = client.get("/api/v1/conversations/999999", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_authorization_forbidden(client, auth_headers, other_user, db: Session):
    # Başka bir kullanıcı için sohbet oluştur
    conversation = Conversation(user_id=other_user.id, title="Secret")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # Kendi token'ımız ile başka kullanıcının sohbetine erişmeye çalış
    response = client.get(f"/api/v1/conversations/{conversation.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_conversation(client, auth_headers, db: Session):
    create_response = client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "Silinecek Sohbet"},
    )
    conversation_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Silindiğinden emin ol
    get_response = client.get(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_chat_query_integration(client, auth_headers, db: Session):
    from unittest.mock import patch
    from types import SimpleNamespace
    
    fake_result = SimpleNamespace(
        question="Fesih süresi nedir?",
        answer="Fesih süresi 30 gündür.",
        model="gemini-test",
        latency_ms=100,
        citations=[],
        used_chunks=[]
    )
    
    with patch("app.api.v1.endpoints.chat.RAGService") as MockRAGService:
        MockRAGService.return_value.query.return_value = fake_result
        
        # Sohbet ID olmadan chat_query çağrıldığında yeni bir sohbet oluşturmalı ve mesajları kaydetmeli
        payload = {
            "question": "Fesih süresi nedir?",
            "top_k": 3
        }
        response = client.post(
            "/api/v1/chat/query",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "conversation_id" in data
        conversation_id = data["conversation_id"]
        assert conversation_id is not None

        # Mesajları kontrol et
        messages_response = client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=auth_headers)
        assert messages_response.status_code == status.HTTP_200_OK
        messages = messages_response.json()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Fesih süresi nedir?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] is not None

        # İkinci soruyu aynı conversation_id ile sor
        fake_result_2 = SimpleNamespace(
            question="Bir soru daha?",
            answer="Cevap 2",
            model="gemini-test",
            latency_ms=100,
            citations=[],
            used_chunks=[]
        )
        MockRAGService.return_value.query.return_value = fake_result_2
        
        payload_2 = {
            "question": "Bir soru daha?",
            "conversation_id": conversation_id,
            "top_k": 3
        }
        response_2 = client.post(
            "/api/v1/chat/query",
            headers=auth_headers,
            json=payload_2,
        )
        assert response_2.status_code == status.HTTP_200_OK
        
        # Toplam mesaj sayısı 4 olmalı
        messages_response_2 = client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=auth_headers)
        messages_2 = messages_response_2.json()
        assert len(messages_2) == 4


def test_cascade_delete(client, auth_headers, db: Session):
    create_response = client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "Cascade Sohbet"},
    )
    conversation_id = create_response.json()["id"]

    # Mesaj ekle
    from unittest.mock import patch
    from types import SimpleNamespace
    
    fake_result = SimpleNamespace(
        question="Test",
        answer="Cevap",
        model="gemini-test",
        latency_ms=100,
        citations=[],
        used_chunks=[]
    )
    with patch("app.api.v1.endpoints.chat.RAGService") as MockRAGService:
        MockRAGService.return_value.query.return_value = fake_result
        client.post(
            "/api/v1/chat/query",
            headers=auth_headers,
            json={"question": "Test", "conversation_id": conversation_id, "top_k": 1},
        )

    messages = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).all()
    assert len(messages) > 0

    # Conversation'ı sil
    client.delete(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)

    # Mesajların silindiğini kontrol et
    messages_after = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).all()
    assert len(messages_after) == 0
