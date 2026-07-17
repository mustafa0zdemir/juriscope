import io

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.storage import get_storage
from app.models.user import User
from app.schemas.chunk import DocumentChunkListResponse, DocumentChunkDetailResponse
from app.schemas.contract import ContractListResponse, ContractResponse, ContractContentResponse, ContractStatusResponse
from app.legal_analysis.schemas.analysis import LegalAnalysisRequest, LegalAnalysisResponse
from app.legal_analysis.services.legal_analysis_service import LegalAnalysisService
from app.services.contract_service import (
    delete_contract,
    download_contract,
    get_contract,
    list_contracts,
)
from app.services.document_processing_service import (
    get_contract_content,
    get_contract_status,
)
from app.services.chunking_service import (
    get_contract_chunks,
    get_chunk_detail,
)
from app.services.embedding_service import trigger_embedding
from app.storage.storage_service import StorageService

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=ContractListResponse)
def get_user_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_contracts(db=db, user_id=current_user.id, skip=skip, limit=limit)


@router.post("/{contract_id}/analyze", response_model=LegalAnalysisResponse)
def analyze_user_contract(
    contract_id: int,
    request: LegalAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LegalAnalysisService().analyze(
        db=db,
        user_id=current_user.id,
        contract_id=contract_id,
        request=request,
    )


@router.get("/{contract_id}/download")
def download_user_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
):
    data, mime_type, original_filename = download_contract(
        db=db, contract_id=contract_id, user_id=current_user.id, storage=storage
    )
    return StreamingResponse(
        content=io.BytesIO(data),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{original_filename}"'},
    )


@router.get("/{contract_id}", response_model=ContractResponse)
def get_single_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_contract(db=db, contract_id=contract_id, user_id=current_user.id)


@router.get("/{contract_id}/content", response_model=ContractContentResponse)
def get_single_contract_content(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_contract_content(db=db, contract_id=contract_id, user_id=current_user.id)


@router.get("/{contract_id}/status", response_model=ContractStatusResponse)
def get_single_contract_status(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_contract_status(db=db, contract_id=contract_id, user_id=current_user.id)


@router.get("/{contract_id}/chunks", response_model=list[DocumentChunkListResponse])
def get_contract_chunks_list(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_contract_chunks(db=db, contract_id=contract_id, user_id=current_user.id)


@router.get("/{contract_id}/chunks/{chunk_id}", response_model=DocumentChunkDetailResponse)
def get_contract_chunk_details(
    contract_id: int,
    chunk_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_chunk_detail(db=db, contract_id=contract_id, chunk_id=chunk_id, user_id=current_user.id)


@router.post("/{contract_id}/embed")
def start_embedding_process(
    contract_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return trigger_embedding(db=db, contract_id=contract_id, user_id=current_user.id, background_tasks=background_tasks)


@router.get("/{contract_id}/embedding/status", response_model=ContractStatusResponse)
def get_contract_embedding_status(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # This returns the current status of the contract which includes 'embedding' and 'embedded'
    return get_contract_status(db=db, contract_id=contract_id, user_id=current_user.id)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
):
    delete_contract(db=db, contract_id=contract_id, user_id=current_user.id, storage=storage)
