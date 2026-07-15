import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.config.settings import settings

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection

    def ensure_collection_exists(self, vector_dimension: int):
        """
        Creates the collection if it doesn't exist, using the provided dimension.
        """
        if not self.client.collection_exists(collection_name=self.collection_name):
            logger.info(f"Creating Qdrant collection '{self.collection_name}' with dimension {vector_dimension}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_dimension, distance=Distance.COSINE),
            )
            logger.info(f"Qdrant collection '{self.collection_name}' created.")
        else:
            logger.info(f"Qdrant collection '{self.collection_name}' already exists.")

    def upsert_vectors(self, points: list[dict[str, Any]]):
        """
        Upserts a list of vector points to Qdrant.
        points should be a list of dicts with:
        'id': string (UUID) or int
        'vector': list[float]
        'payload': dict
        """
        qdrant_points = [
            PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p["payload"]
            )
            for p in points
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=qdrant_points
        )
