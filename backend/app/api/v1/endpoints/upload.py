from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.contract import ContractCreateResponse
from app.services.contract_service import upload_contract

router = APIRouter(tags=["Upload"])


@router.post("/upload", response_model=ContractCreateResponse)
async def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await upload_contract(db=db, file=file, current_user=current_user)
