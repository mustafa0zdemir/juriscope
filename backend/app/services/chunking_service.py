import logging
import traceback

from app.chunking.fixed_size_strategy import FixedSizeChunkStrategy
from app.database.session import SessionLocal
from app.repositories.contract_repository import ContractRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_content_repository import DocumentContentRepository

logger = logging.getLogger(__name__)


def process_chunking_task(contract_id: int) -> None:
    """
    Background task to chunk the parsed document content.
    """
    db = SessionLocal()
    try:
        repo = ContractRepository(db)
        contract = repo.get_by_id(contract_id)

        if not contract:
            logger.error(f"Contract {contract_id} not found for chunking.")
            return

        # Update status to chunking
        repo.update_status(contract, "chunking")

        content_repo = DocumentContentRepository(db)
        content = content_repo.get_by_contract_id(contract_id)

        if not content or not content.extracted_text.strip():
            logger.error(f"No content found or content is empty for contract {contract_id}")
            repo.update_status(contract, "failed")
            return

        # Initialize Strategy
        strategy = FixedSizeChunkStrategy(chunk_size=1000, chunk_overlap=200)
        chunks_text = strategy.chunk(content.extracted_text)

        if not chunks_text:
            logger.error(f"Failed to generate chunks for contract {contract_id}")
            repo.update_status(contract, "failed")
            return

        chunks_data = []
        start_char_idx = 0
        
        for idx, text in enumerate(chunks_text):
            char_count = len(text)
            token_count = char_count // 4  # simple heuristic for now
            end_char_idx = start_char_idx + char_count
            
            metadata = {
                "start_char": start_char_idx,
                "end_char": end_char_idx,
                "parser": content.parser,
                "chunk_strategy": "FixedSizeChunkStrategy",
                "language": content.language,
                "page": content.page_count if content.page_count == 1 else None # specific page logic can be complex
            }

            chunks_data.append({
                "chunk_index": idx,
                "text": text,
                "page_number": content.page_count if content.page_count == 1 else None,
                "token_count": token_count,
                "char_count": char_count,
                "metadata": metadata
            })
            
            start_char_idx += (1000 - 200) # next start char based on chunk strategy

        chunk_repo = DocumentChunkRepository(db)
        chunk_repo.create_bulk(
            contract_id=contract.id,
            content_id=content.id,
            chunks_data=chunks_data
        )

        repo.update_status(contract, "chunked")
        logger.info(f"Successfully chunked contract {contract_id} into {len(chunks_data)} chunks.")

    except Exception as e:
        logger.error(f"Failed to chunk contract {contract_id}: {str(e)}")
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


def get_contract_chunks(db: SessionLocal, contract_id: int, user_id: int):
    from app.core.exceptions import ForbiddenException, NotFoundException
    from app.schemas.chunk import DocumentChunkListResponse
    
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")

    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to access this contract")

    chunk_repo = DocumentChunkRepository(db)
    chunks = chunk_repo.list_by_contract_id(contract_id)

    return [
        DocumentChunkListResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            char_count=c.char_count,
            token_count=c.token_count,
            page_number=c.page_number
        ) for c in chunks
    ]


def get_chunk_detail(db: SessionLocal, contract_id: int, chunk_id: int, user_id: int):
    from app.core.exceptions import ForbiddenException, NotFoundException
    from app.schemas.chunk import DocumentChunkDetailResponse
    
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")

    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to access this contract")

    chunk_repo = DocumentChunkRepository(db)
    chunk = chunk_repo.get_by_id(chunk_id)

    if not chunk or chunk.contract_id != contract_id:
        raise NotFoundException(detail="Chunk not found")

    return DocumentChunkDetailResponse(
        id=chunk.id,
        contract_id=chunk.contract_id,
        content_id=chunk.content_id,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        page_number=chunk.page_number,
        token_count=chunk.token_count,
        char_count=chunk.char_count,
        metadata=chunk.metadata_
    )
