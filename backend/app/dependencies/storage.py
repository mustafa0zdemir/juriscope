from app.storage.providers.minio_provider import MinioProvider
from app.storage.storage_service import StorageService


def get_storage() -> StorageService:
    provider = MinioProvider()
    return StorageService(provider=provider)
