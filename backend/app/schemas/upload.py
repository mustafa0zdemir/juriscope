from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str
    message: str = "File uploaded successfully"
