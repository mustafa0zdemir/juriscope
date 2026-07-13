from fastapi import APIRouter, UploadFile

from app.schemas.upload import UploadResponse
from app.services.upload_service import save_upload_file

router = APIRouter(tags=["Upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile):
    return await save_upload_file(file)
