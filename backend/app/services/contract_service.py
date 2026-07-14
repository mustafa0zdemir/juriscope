import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import BadRequestException, NotFoundException, ForbiddenException
from app.models.user import User
from app.repositories.contract_repository import ContractRepository
from app.schemas.contract import ContractCreateResponse, ContractListResponse, ContractResponse


async def upload_contract(db: Session, file: UploadFile, current_user: User) -> ContractCreateResponse:
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

    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path_obj = settings.upload_path / unique_filename
    file_path = str(file_path_obj.absolute())

    file_path_obj.write_bytes(content)

    mime_type = file.content_type or "application/octet-stream"

    repo = ContractRepository(db)
    contract = repo.create(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_filename=unique_filename,
        file_path=file_path,
        mime_type=mime_type,
        file_size=file_size,
    )

    return ContractCreateResponse.model_validate(contract)


def list_contracts(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> ContractListResponse:
    repo = ContractRepository(db)
    contracts = repo.list_by_user(user_id, skip=skip, limit=limit)
    
    # We can get total count from DB but for now we just return the list length
    # In a real app we would add a count method to the repository
    return ContractListResponse(
        items=[ContractResponse.model_validate(c) for c in contracts],
        total=len(contracts) # Note: this is just the paginated total unless a count method is used
    )


def get_contract(db: Session, contract_id: int, user_id: int) -> ContractResponse:
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")
    
    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to access this contract")

    return ContractResponse.model_validate(contract)


def delete_contract(db: Session, contract_id: int, user_id: int) -> None:
    repo = ContractRepository(db)
    contract = repo.get_by_id(contract_id)

    if not contract:
        raise NotFoundException(detail="Contract not found")
    
    if contract.user_id != user_id:
        raise ForbiddenException(detail="You do not have permission to delete this contract")

    # Delete the physical file
    try:
        if os.path.exists(contract.file_path):
            os.remove(contract.file_path)
    except Exception as e:
        # We might want to log this but we still want to delete the DB record
        pass

    # Delete DB record
    repo.delete(contract)
