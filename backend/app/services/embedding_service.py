import logging
import traceback
import uuid

from app.database.session import SessionLocal
from app.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from app.repositories.contract_repository import ContractRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.storage.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


def process_embedding_task(contract_id: int) -> None:
    """
    Background task to embed chunks and save them to Qdrant.
    """
    db = SessionLocal()
    try:
        repo = ContractRepository(db)
        contract = repo.get_by_id(contract_id)

        if not contract:
            logger.error(f"Contract {contract_id} not found for embedding.")
            return

        # Update status to embedding
        repo.update_status(contract, "embedding")

        chunk_repo = DocumentChunkRepository(db)
        chunks = chunk_repo.list_by_contract_id(contract_id)

        if not chunks:
            logger.error(f"No chunks found for contract {contract_id}")
            repo.update_status(contract, "failed")
            return

        embed_provider = SentenceTransformerProvider.get_instance()
        qdrant_service = QdrantService()

        points = []
        for chunk in chunks:
            # Embed the text
            vector = embed_provider.embed_text(chunk.text)

            # Create payload
            payload = {
                "contract_id": contract.id,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "language": chunk.metadata_.get("language"),
                "parser": chunk.metadata_.get("parser"),
                "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
                "text": chunk.text, # It's often useful to store the text in the vector DB for easy retrieval
            }

            # We use a UUID string based on the chunk id to ensure uniqueness
            point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"chunk_{chunk.id}"))

            points.append({
                "id": point_id,
                "vector": vector,
                "payload": payload
            })

        # Upsert all vectors to Qdrant
        qdrant_service.upsert_vectors(points)

        # Update status to embedded
        repo.update_status(contract, "embedded")
        logger.info(f"Successfully embedded and saved {len(points)} vectors for contract {contract_id}.")

    except Exception as e:
        logger.error(f"Failed to embed contract {contract_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        try:
            repo = ContractRepository(db)
            contract = repo.get_by_id(contract_id)
            if contract:
                repo.update_status(contract, "failed")
        except Exception as inner_e:
            logger.error(f"Failed to update contract status to failed: {str(inner_e)}")
    finally:
        db.close()


def trigger_embedding(db: SessionLocal, contract_id: int, user_id: int, background_tasks):
    from app.core.exceptions import ForbiddenException, NotFoundException
    
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")

    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to access this contract")

    background_tasks.add_task(process_embedding_task, contract_id)
    return {"message": "Embedding process started in the background"}
