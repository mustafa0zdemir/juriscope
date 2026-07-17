from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_admin
from app.dependencies.database import get_db
from app.dependencies.storage import get_storage
from app.legal_kb.ingestion.legal_ingestion_service import LegalIngestionService
from app.legal_kb.models.legal_document import LegalDocumentType
from app.legal_kb.schemas.legal_document import LegalDocumentListResponse, LegalDocumentResponse
from app.legal_kb.services.legal_document_service import LegalDocumentService
from app.schemas.auth import UserResponse
from app.storage.storage_service import StorageService

router = APIRouter(prefix="/legal", tags=["Legal Knowledge Base"])


@router.post("/upload", response_model=LegalDocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_legal_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: LegalDocumentType = Form(...),
    source: str = Form(...),
    official_number: str | None = Form(None),
    publication_date: date | None = Form(None),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    current_user: UserResponse = Depends(require_admin),
):
    del current_user
    document = await LegalIngestionService().upload(
        db=db,
        file=file,
        title=title,
        document_type=document_type,
        source=source,
        official_number=official_number,
        publication_date=publication_date,
        background_tasks=background_tasks,
        storage=storage,
    )
    return LegalDocumentResponse.model_validate(document)


@router.get("", response_model=LegalDocumentListResponse)
def list_legal_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    del current_user
    return LegalDocumentService().list_documents(db=db, skip=skip, limit=limit)


@router.get("/{document_id}", response_model=LegalDocumentResponse)
def get_legal_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin),
):
    del current_user
    return LegalDocumentService().get_document(db=db, document_id=document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_legal_document(
    document_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    current_user: UserResponse = Depends(require_admin),
):
    del current_user
    LegalDocumentService().delete_document(db=db, document_id=document_id, storage=storage)
