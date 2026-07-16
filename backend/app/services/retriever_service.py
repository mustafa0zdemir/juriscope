import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from app.repositories.contract_repository import ContractRepository
from app.retrieval.base import SearchResult

if TYPE_CHECKING:
    from app.retrieval.qdrant_retriever import QdrantRetriever

logger = logging.getLogger(__name__)


class RetrieverService:
    def __init__(self, retriever: "QdrantRetriever | None" = None) -> None:
        if retriever is None:
            from app.retrieval.qdrant_retriever import QdrantRetriever

            retriever = QdrantRetriever()
        self.retriever = retriever

    def retrieve(
        self,
        db: Session,
        question: str,
        user_id: int,
        contract_ids: list[int] | None = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        contract_repository = ContractRepository(db)
        if contract_ids is None:
            contracts = contract_repository.list_by_user(user_id=user_id, limit=10000)
            authorized_contract_ids = [contract.id for contract in contracts]
        else:
            authorized_contract_ids = self._validate_contract_access(
                contract_repository, contract_ids, user_id
            )

        if not authorized_contract_ids:
            return []

        try:
            embedding_provider = SentenceTransformerProvider.get_instance()
            query_vector = embedding_provider.embed_text(question)
            return self.retriever.search(
                query_vector=query_vector,
                contract_ids=authorized_contract_ids,
                top_k=top_k,
            )
        except Exception:
            logger.exception("RAG retrieval failed")
            raise

    @staticmethod
    def _validate_contract_access(repository: ContractRepository, contract_ids: list[int], user_id: int) -> list[int]:
        authorized_ids: list[int] = []
        for contract_id in dict.fromkeys(contract_ids):
            contract = repository.get_by_id(contract_id)
            if not contract:
                raise NotFoundException(detail="Sözleşme bulunamadı")
            if contract.user_id != user_id:
                raise ForbiddenException(detail="Bu sözleşmeye erişim yetkiniz yok")
            authorized_ids.append(contract.id)
        return authorized_ids
