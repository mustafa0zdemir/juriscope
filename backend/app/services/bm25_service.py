import math
import re
from collections import Counter

from sqlalchemy.orm import Session

from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.retrieval.base import SearchResult


class BM25Service:
    """Builds an in-memory Okapi BM25 index over authorized document chunks."""

    def __init__(self, chunk_repository: DocumentChunkRepository | None = None) -> None:
        self.chunk_repository = chunk_repository

    def search(
        self,
        db: Session,
        question: str,
        contract_ids: list[int],
        top_k: int,
    ) -> list[SearchResult]:
        repository = self.chunk_repository or DocumentChunkRepository(db)
        chunks = repository.list_by_contract_ids(contract_ids)
        query_tokens = self.tokenize(question)
        if not chunks or not query_tokens:
            return []

        documents = [self.tokenize(chunk.text) for chunk in chunks]
        scores = self._score(query_tokens, documents)
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)

        results: list[SearchResult] = []
        for index, score in ranked[:top_k]:
            if score <= 0:
                continue
            chunk = chunks[index]
            results.append(
                SearchResult(
                    score=score,
                    chunk_id=chunk.id,
                    contract_id=chunk.contract_id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    metadata=chunk.metadata_,
                    keyword_score=score,
                )
            )
        return results

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)

    @staticmethod
    def _score(
        query_tokens: list[str], documents: list[list[str]], k1: float = 1.5, b: float = 0.75
    ) -> list[float]:
        document_count = len(documents)
        document_lengths = [len(document) for document in documents]
        average_length = sum(document_lengths) / document_count if document_count else 0
        document_frequencies: Counter[str] = Counter()
        term_frequencies: list[Counter[str]] = []

        for document in documents:
            frequencies = Counter(document)
            term_frequencies.append(frequencies)
            document_frequencies.update(frequencies.keys())

        scores: list[float] = []
        for length, frequencies in zip(document_lengths, term_frequencies, strict=True):
            score = 0.0
            for token in query_tokens:
                frequency = frequencies[token]
                if not frequency:
                    continue
                inverse_frequency = math.log(
                    1 + (document_count - document_frequencies[token] + 0.5)
                    / (document_frequencies[token] + 0.5)
                )
                denominator = frequency + k1 * (1 - b + b * length / average_length)
                score += inverse_frequency * (frequency * (k1 + 1) / denominator)
            scores.append(score)
        return scores
