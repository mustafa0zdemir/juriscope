import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup test DB before app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database.base import Base
from app.application import create_app
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage
from app.models.contract import Contract
from app.models.document_content import DocumentContent
from app.models.document_chunk import DocumentChunk


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    print("Registered tables before create_all:", Base.metadata.tables.keys())
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    yield db_session
    db_session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def current_user(db):
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def client(db, current_user):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return current_user

    with patch("app.storage.providers.minio_provider.Minio"), patch("app.storage.qdrant_service.QdrantClient"), patch("app.application.SentenceTransformerProvider"):
        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        with TestClient(app) as test_client:
            yield test_client
            
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers():
    return {"Authorization": "Bearer test-token"}
