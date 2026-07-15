import io

from minio import Minio
from minio.error import S3Error

from app.config.settings import settings
from app.storage.providers.base_provider import BaseStorageProvider


class MinioProvider(BaseStorageProvider):

    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket_name

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return key

    def download(self, key: str) -> bytes:
        try:
            response = self._client.get_object(self._bucket, key)
            return response.read()
        except S3Error as exc:
            raise FileNotFoundError(f"Object not found in storage: {key}") from exc
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        try:
            self._client.remove_object(self._bucket, key)
        except S3Error:
            pass
