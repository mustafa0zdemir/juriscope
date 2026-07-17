import logging
import uuid
from datetime import date
from pathlib import Path

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session

from app.chunking.fixed_size_strategy import FixedSizeChunkStrategy
from app.config.settings import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.database.session import SessionLocal
from app.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from app.legal_kb.models.legal_document import LegalDocument, LegalDocumentType
from app.legal_kb.repositories.legal_chunk_repository import LegalChunkRepository
from app.legal_kb.repositories.legal_document_repository import LegalDocumentRepository
from app.legal_kb.utils.metadata import build_legal_metadata
from app.parsers.factory import get_parser
from app.storage.providers.minio_provider import MinioProvider
from app.storage.qdrant_service import QdrantService
from app.storage.storage_service import StorageService

logger = logging.getLogger(__name__)


class LegalIngestionService:
    ALLOWED_EXTENSIONS = {".pdf", ".docx"}

    async def upload(
        self,
        db: Session,
        file: UploadFile,
        title: str,
        document_type: LegalDocumentType,
        source: str,
        official_number: str | None,
        publication_date: date | None,
        background_tasks: BackgroundTasks,
        storage: StorageService,
    ) -> LegalDocument:
        if not file.filename:
            raise BadRequestException(detail="Dosya adı zorunludur")
        extension = Path(file.filename).suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise BadRequestException(detail="Legal belgelerde yalnızca PDF ve DOCX desteklenir")

        content = await file.read()
        if not content:
            raise BadRequestException(detail="Boş dosya yüklenemez")
        if len(content) > settings.max_upload_size_bytes:
            raise BadRequestException(detail="Dosya boyutu izin verilen limiti aşıyor")

        storage_key = f"legal/{document_type.value.lower()}/{uuid.uuid4().hex}{extension}"
        mime_type = file.content_type or "application/octet-stream"
        storage.upload(storage_key, content, mime_type)
        document = LegalDocumentRepository(db).create(
            title=title,
            document_type=document_type,
            source=source,
            official_number=official_number,
            publication_date=publication_date,
            original_filename=file.filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=len(content),
        )
        background_tasks.add_task(process_legal_document_task, document.id)
        return document


def process_legal_document_task(document_id: int) -> None:
    db = SessionLocal()
    repository = LegalDocumentRepository(db)
    try:
        document = repository.get_by_id(document_id)
        if not document:
            raise NotFoundException(detail="Legal belge bulunamadı")
        repository.update_status(document, "processing")

        storage = StorageService(MinioProvider())
        content = storage.download(document.storage_key)
        extension = Path(document.original_filename).suffix.lower()
        text, page_count, parser_name = get_parser(extension).parse(content)
        chunks = FixedSizeChunkStrategy().chunk(text)
        if not chunks:
            raise ValueError("Legal belgeden metin chunk'ı üretilemedi")

        chunk_repository = LegalChunkRepository(db)
        legal_chunks = chunk_repository.create_bulk(
            document_id=document.id,
            chunks_data=[
                {
                    "chunk_index": index,
                    "text": chunk_text,
                    "page_number": None,
                    "token_count": len(chunk_text.split()),
                    "metadata": {
                        **build_legal_metadata(document, chunk_text),
                        "parser": parser_name,
                        "page_count": page_count,
                    },
                }
                for index, chunk_text in enumerate(chunks)
            ],
        )

        embedding_provider = SentenceTransformerProvider.get_instance()
        qdrant = QdrantService(settings.legal_collection)
        qdrant.upsert_vectors(
            [
                {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_OID, f"legal_chunk_{chunk.id}")),
                    "vector": embedding_provider.embed_text(chunk.text),
                    "payload": {
                        **chunk.metadata_,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "text": chunk.text,
                    },
                }
                for chunk in legal_chunks
            ]
        )
        chunk_repository.mark_embedded(legal_chunks)
        repository.update_status(document, "embedded")
    except Exception:
        logger.exception("Legal belge ingestion başarısız: %s", document_id)
        document = repository.get_by_id(document_id)
        if document:
            repository.update_status(document, "failed")
    finally:
        db.close()
