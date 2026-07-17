import logging

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from app.repositories.contract_repository import ContractRepository
from app.retrieval.base import SearchResult
from app.config.settings import settings
from app.retrieval.hybrid_retriever import HybridRetriever, HybridSearchResult, RetrievalDebug

logger = logging.getLogger(__name__)


class RetrieverService:
    def __init__(self, hybrid_retriever: HybridRetriever | None = None) -> None:
        self.hybrid_retriever = hybrid_retriever or HybridRetriever()

    def retrieve(
        self,
        db: Session,
        question: str,
        user_id: int,
        contract_ids: list[int] | None = None,
        top_k: int = 5,
        search_mode: str = settings.default_search_mode,
    ) -> list[SearchResult]:
        return self.retrieve_with_debug(
            db=db,
            question=question,
            user_id=user_id,
            contract_ids=contract_ids,
            top_k=top_k,
            search_mode=search_mode,
        ).results

    def retrieve_with_debug(
        self,
        db: Session,
        question: str,
        user_id: int,
        contract_ids: list[int] | None = None,
        top_k: int = 5,
        search_mode: str = settings.default_search_mode,
    ) -> HybridSearchResult:
        if search_mode not in {"vector", "keyword", "hybrid"}:
            raise ValueError("Geçersiz arama modu")

        contract_repository = ContractRepository(db)
        if contract_ids is None:
            contracts = contract_repository.list_by_user(user_id=user_id, limit=10000)
            authorized_contract_ids = [contract.id for contract in contracts]
        else:
            authorized_contract_ids = self._validate_contract_access(
                contract_repository, contract_ids, user_id
            )

        if not authorized_contract_ids:
            return HybridSearchResult(
                results=[],
                debug=RetrievalDebug(vector_hits=[], keyword_hits=[], merged_hits=[]),
            )

        try:
            query_vector = None
            if search_mode in {"vector", "hybrid"}:
                embedding_provider = SentenceTransformerProvider.get_instance()
                query_vector = embedding_provider.embed_text(question)
            return self.hybrid_retriever.search(
                db=db,
                question=question,
                contract_ids=authorized_contract_ids,
                query_vector=query_vector,
                search_mode=search_mode,
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
