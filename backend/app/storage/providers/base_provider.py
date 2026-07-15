from abc import ABC, abstractmethod


class BaseStorageProvider(ABC):

    @abstractmethod
    def ensure_bucket(self) -> None: ...

    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str) -> str: ...

    @abstractmethod
    def download(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...
