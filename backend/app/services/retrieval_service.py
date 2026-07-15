import logging

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from app.repositories.contract_repository import ContractRepository
from app.retrieval.qdrant_retriever import QdrantRetriever
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem

logger = logging.getLogger(__name__)


def semantic_search(
    db: Session,
    request: SearchRequest,
    user_id: int,
) -> SearchResponse:
    # 1. Validate contract_id ownership if provided
    contract_id_filter: int | None = None
    if request.contract_id is not None:
        repo = ContractRepository(db)
        contract = repo.get_by_id(request.contract_id)
        if not contract:
            raise NotFoundException(detail="Sözleşme bulunamadı")
        if contract.user_id != user_id:
            raise ForbiddenException(detail="Bu sözleşmeye erişim yetkiniz yok")
        contract_id_filter = request.contract_id

    # 2. Get all user contract IDs for authorization filter
    repo = ContractRepository(db)
    user_contracts = repo.list_by_user(user_id=user_id, limit=10000)
    contract_ids = [c.id for c in user_contracts]

    if not contract_ids:
        return SearchResponse(query=request.query, results=[], total=0)

    # 3. Embed the query using the singleton model
    try:
        embed_provider = SentenceTransformerProvider.get_instance()
        query_vector = embed_provider.embed_text(request.query)
    except Exception as e:
        logger.error(f"Sorgu embedding üretilemedi: {str(e)}")
        raise

    # 4. Perform semantic search via QdrantRetriever
    try:
        retriever = QdrantRetriever()
        results = retriever.search(
            query_vector=query_vector,
            contract_ids=contract_ids,
            top_k=request.top_k,
            contract_id_filter=contract_id_filter,
        )
    except Exception as e:
        logger.error(f"Qdrant arama hatası: {str(e)}")
        raise

    # 5. Map to response schema
    result_items = [
        SearchResultItem(
            score=r.score,
            chunk_id=r.chunk_id,
            contract_id=r.contract_id,
            chunk_index=r.chunk_index,
            page_number=r.page_number,
            text=r.text,
            metadata=r.metadata,
        )
        for r in results
    ]

    return SearchResponse(
        query=request.query,
        results=result_items,
        total=len(result_items),
    )
