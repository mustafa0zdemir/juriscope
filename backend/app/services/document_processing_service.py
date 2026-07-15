import logging
import traceback
from pathlib import Path

from app.database.session import SessionLocal
from app.parsers.factory import get_parser
from app.repositories.contract_repository import ContractRepository
from app.repositories.document_content_repository import DocumentContentRepository
from app.storage.providers.minio_provider import MinioProvider
from app.storage.storage_service import StorageService

logger = logging.getLogger(__name__)


def process_document_background_task(contract_id: int) -> None:
    """
    Background task to process the document.
    Downloads the document from MinIO, parses it, creates DocumentContent,
    and updates the contract status.
    """
    db = SessionLocal()
    try:
        repo = ContractRepository(db)
        contract = repo.get_by_id(contract_id)

        if not contract:
            logger.error(f"Contract {contract_id} not found for background processing.")
            return

        # Update status to parsing
        repo.update_status(contract, "parsing")

        # Initialize storage service (could also pass these as args, but this is simple)
        storage_provider = MinioProvider()
        storage = StorageService(storage_provider)

        # Download file
        file_content = storage.download(contract.storage_key)

        # Determine extension and get parser
        file_extension = Path(contract.original_filename).suffix
        parser = get_parser(file_extension)

        # Parse document
        extracted_text, page_count, parser_name = parser.parse(file_content)

        # Create DocumentContent
        content_repo = DocumentContentRepository(db)
        content_repo.create(
            contract_id=contract.id,
            extracted_text=extracted_text,
            page_count=page_count,
            parser=parser_name,
            language="tr"
        )

        # Update status to parsed
        repo.update_status(contract, "parsed")
        logger.info(f"Successfully processed contract {contract_id}")

        # Trigger chunking process
        from app.services.chunking_service import process_chunking_task
        process_chunking_task(contract_id)

    except Exception as e:
        logger.error(f"Failed to process contract {contract_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Try to update status to failed
        try:
            repo = ContractRepository(db)
            contract = repo.get_by_id(contract_id)
            if contract:
                repo.update_status(contract, "failed")
        except Exception as inner_e:
            logger.error(f"Failed to update contract status to failed: {str(inner_e)}")
    finally:
        db.close()


def get_contract_content(db: SessionLocal, contract_id: int, user_id: int):
    from app.core.exceptions import ForbiddenException, NotFoundException
    from app.schemas.contract import ContractContentResponse
    
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")

    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to access this contract")

    content_repo = DocumentContentRepository(db)
    content = content_repo.get_by_contract_id(contract_id)

    if not content:
        raise NotFoundException(detail="Content not available for this contract yet")

    return ContractContentResponse(
        contract_id=content.contract_id,
        page_count=content.page_count,
        parser=content.parser,
        language=content.language,
        text=content.extracted_text,
    )


def get_contract_status(db: SessionLocal, contract_id: int, user_id: int):
    from app.core.exceptions import ForbiddenException, NotFoundException
    from app.schemas.contract import ContractStatusResponse
    
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")

    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to access this contract")

    return ContractStatusResponse(
        contract_id=contract.id,
        status=contract.status,
    )
