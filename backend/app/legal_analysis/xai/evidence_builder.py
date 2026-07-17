from app.legal_analysis.schemas.analysis import LegalAnalysisResponse, RiskItem
from app.legal_analysis.xai.schemas import AttributedSource, EvidenceItem, LegalReasoning
from app.retrieval.base import SearchResult


CASE_TYPES = {"SUPREME_COURT", "COUNCIL_OF_STATE", "CONSTITUTIONAL_COURT"}


class EvidenceBuilder:
    def build(
        self,
        analysis: LegalAnalysisResponse,
        chunks: list[SearchResult],
    ) -> tuple[list[EvidenceItem], list[LegalReasoning]]:
        contracts = [chunk for chunk in chunks if chunk.source_type == "contract"]
        laws = [chunk for chunk in chunks if chunk.source_type == "legal" and chunk.metadata.get("document_type") not in CASE_TYPES]
        cases = [chunk for chunk in chunks if chunk.metadata.get("document_type") in CASE_TYPES]
        evidence: list[EvidenceItem] = []
        reasoning: list[LegalReasoning] = []

        for risk in analysis.risks:
            primary = self._cited_chunk(risk, chunks)
            contract = primary if primary and primary.source_type == "contract" else self._best(contracts)
            law = primary if primary and primary in laws else self._best(laws)
            case = primary if primary and primary in cases else self._best(cases)
            scored = primary or contract or law or case
            item = EvidenceItem(
                risk_title=risk.title,
                contract_chunk=self.to_source(contract),
                law_chunk=self.to_source(law),
                case_law_chunk=self.to_source(case),
                similarity_score=self._similarity(scored),
                rerank_score=scored.rerank_score if scored else None,
            )
            evidence.append(item)
            reasoning.append(self._reasoning(risk, item))
        return evidence, reasoning

    def sources(self, chunks: list[SearchResult]) -> tuple[list[AttributedSource], list[AttributedSource], list[AttributedSource]]:
        contracts = [self.to_source(chunk) for chunk in chunks if chunk.source_type == "contract"]
        laws = [self.to_source(chunk) for chunk in chunks if chunk.source_type == "legal" and chunk.metadata.get("document_type") not in CASE_TYPES]
        cases = [self.to_source(chunk) for chunk in chunks if chunk.metadata.get("document_type") in CASE_TYPES]
        return (
            [source for source in contracts if source],
            [source for source in laws if source],
            [source for source in cases if source],
        )

    @staticmethod
    def to_source(chunk: SearchResult | None) -> AttributedSource | None:
        if chunk is None:
            return None
        metadata = chunk.metadata
        title = metadata.get("title") or (
            f"Sözleşme #{chunk.contract_id}" if chunk.source_type == "contract" else "Hukuki kaynak"
        )
        return AttributedSource(
            source_type=EvidenceBuilder._source_group(chunk),
            title=title,
            article=metadata.get("article"),
            page=chunk.page_number,
            chunk=chunk.chunk_index,
            similarity=EvidenceBuilder._similarity(chunk),
            rerank_score=chunk.rerank_score,
            text_excerpt=chunk.text[:320],
        )

    @staticmethod
    def _cited_chunk(risk: RiskItem, chunks: list[SearchResult]) -> SearchResult | None:
        if not risk.citation or risk.citation > len(chunks):
            return None
        return chunks[risk.citation - 1]

    @staticmethod
    def _best(chunks: list[SearchResult]) -> SearchResult | None:
        return max(chunks, key=lambda chunk: chunk.score, default=None)

    @staticmethod
    def _similarity(chunk: SearchResult | None) -> float:
        if not chunk:
            return 0.0
        return max(0.0, float(chunk.vector_score if chunk.vector_score is not None else chunk.score))

    @staticmethod
    def _source_group(chunk: SearchResult) -> str:
        if chunk.source_type == "contract":
            return "contract"
        return "case_law" if chunk.metadata.get("document_type") in CASE_TYPES else "law"

    @staticmethod
    def _reasoning(risk: RiskItem, evidence: EvidenceItem) -> LegalReasoning:
        law_basis = (
            f"{evidence.law_chunk.title}"
            + (f" Madde {evidence.law_chunk.article}" if evidence.law_chunk.article else "")
            if evidence.law_chunk
            else "Eşleşen açık bir kanun maddesi bulunamadı."
        )
        case_support = evidence.case_law_chunk.title if evidence.case_law_chunk else "Destekleyici emsal karar bulunamadı."
        affected = evidence.contract_chunk.text_excerpt if evidence.contract_chunk else "Etkilenen sözleşme maddesi belirlenemedi."
        return LegalReasoning(
            risk_title=risk.title,
            why_risky=f"{risk.reason} {risk.description}",
            law_basis=law_basis,
            case_support=case_support,
            affected_clause=affected,
        )
