import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.user import User
from app.repositories.contract_repository import ContractRepository
from app.schemas.contract import ContractCreateResponse, ContractListResponse, ContractResponse
from app.services.document_processing_service import process_document_background_task
from app.storage.storage_service import StorageService


async def upload_contract(
    db: Session, file: UploadFile, current_user: User, storage: StorageService, background_tasks: BackgroundTasks
) -> ContractCreateResponse:
    if not file.filename:
        raise BadRequestException(detail="Filename is required")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in settings.allowed_extensions:
        raise BadRequestException(
            detail=f"Invalid file type. Allowed types: {', '.join(settings.allowed_extensions)}"
        )

    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_upload_size_bytes:
        raise BadRequestException(
            detail=f"File size exceeds maximum allowed size of {settings.max_upload_size_mb}MB"
        )

    unique_id = uuid.uuid4().hex
    stored_filename = f"{unique_id}{file_extension}"
    now = datetime.utcnow()
    storage_key = f"contracts/{now.year}/{now.month:02d}/{stored_filename}"
    mime_type = file.content_type or "application/octet-stream"

    storage.upload(key=storage_key, data=content, content_type=mime_type)

    repo = ContractRepository(db)
    contract = repo.create(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=file_size,
    )

    background_tasks.add_task(process_document_background_task, contract.id)

    return ContractCreateResponse.model_validate(contract)


def list_contracts(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> ContractListResponse:
    repo = ContractRepository(db)
    contracts = repo.list_by_user(user_id, skip=skip, limit=limit)
    return ContractListResponse(
        items=[ContractResponse.model_validate(c) for c in contracts],
        total=len(contracts),
    )


def get_contract(db: Session, contract_id: int, user_id: int) -> ContractResponse:
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")

    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to access this contract")

    return ContractResponse.model_validate(contract)


def download_contract(
    db: Session, contract_id: int, user_id: int, storage: StorageService
) -> tuple[bytes, str, str]:
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")

    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to access this contract")

    data = storage.download(contract.storage_key)
    return data, contract.mime_type, contract.original_filename


def delete_contract(
    db: Session, contract_id: int, user_id: int, storage: StorageService
) -> None:
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")

    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to delete this contract")

    storage.delete(contract.storage_key)
    repo.delete(contract)
