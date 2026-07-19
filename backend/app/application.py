from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.config.settings import settings
from app.storage.providers.minio_provider import MinioProvider
from app.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from app.storage.qdrant_service import QdrantService
from app.middleware.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init MinIO
    provider = MinioProvider()
    provider.ensure_bucket()

    # Init Embedding Model (Singleton)
    embed_provider = SentenceTransformerProvider(settings.embedding_model)
    
    # Init Qdrant Collection
    qdrant = QdrantService()
    qdrant.ensure_collection_exists(embed_provider.get_dimension())
    if settings.enable_legal_search:
        legal_qdrant = QdrantService(settings.legal_collection)
        legal_qdrant.ensure_collection_exists(embed_provider.get_dimension())

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(api_v1_router, prefix="/api/v1")

    return app
