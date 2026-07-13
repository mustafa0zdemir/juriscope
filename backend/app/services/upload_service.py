import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config.settings import settings
from app.core.exceptions import BadRequestException
from app.schemas.upload import UploadResponse


async def save_upload_file(file: UploadFile) -> UploadResponse:
    if not file.filename:
        raise BadRequestException(detail="Filename is required")

    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_upload_size_bytes:
        raise BadRequestException(
            detail=f"File size exceeds maximum allowed size of {settings.max_upload_size_mb}MB"
        )

    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = settings.upload_path / unique_filename

    file_path.write_bytes(content)

    return UploadResponse(
        filename=unique_filename,
        size=file_size,
        content_type=file.content_type or "application/octet-stream",
    )
