from app.storage.providers.base_provider import BaseStorageProvider


class StorageService:

    def __init__(self, provider: BaseStorageProvider) -> None:
        self._provider = provider

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        return self._provider.upload(key, data, content_type)

    def download(self, key: str) -> bytes:
        return self._provider.download(key)

    def delete(self, key: str) -> None:
        self._provider.delete(key)
