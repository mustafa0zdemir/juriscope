import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.advanced_analysis.schemas import (
    ClauseChange,
    ClauseType,
    ContractComparisonRequest,
    ContractComparisonResponse,
    DetectedClause,
    RiskChange,
)
from app.advanced_analysis.services.clause_detection_service import ClauseDetectionService


class ContractComparisonService:
    def __init__(self, clause_service: ClauseDetectionService | None = None) -> None:
        self.clause_service = clause_service or ClauseDetectionService()

    def compare(
        self,
        db: Session,
        user_id: int,
        request: ContractComparisonRequest,
    ) -> ContractComparisonResponse:
        if request.base_contract_id == request.comparison_contract_id:
            raise ValueError("Karşılaştırma için iki farklı sözleşme seçilmelidir")
        base = self.clause_service.detect(db, user_id, request.base_contract_id)
        comparison = self.clause_service.detect(db, user_id, request.comparison_contract_id)
        before_map = self._best_by_type(base.clauses)
        after_map = self._best_by_type(comparison.clauses)
        added = [after_map[key] for key in after_map.keys() - before_map.keys()]
        removed = [before_map[key] for key in before_map.keys() - after_map.keys()]
        modified: list[ClauseChange] = []
        unchanged: list[ClauseType] = []
        risk_changes: list[RiskChange] = [
            RiskChange(
                clause_type=clause.clause_type,
                before_tags=[],
                after_tags=clause.risk_tags,
                direction="ADDED",
            )
            for clause in added
        ] + [
            RiskChange(
                clause_type=clause.clause_type,
                before_tags=clause.risk_tags,
                after_tags=[],
                direction="REMOVED",
            )
            for clause in removed
        ]

        for clause_type in before_map.keys() & after_map.keys():
            before = before_map[clause_type]
            after = after_map[clause_type]
            similarity = SequenceMatcher(None, self._normalize(before.text), self._normalize(after.text)).ratio()
            if similarity < 0.92:
                modified.append(
                    ClauseChange(
                        clause_type=clause_type,
                        before=before,
                        after=after,
                        similarity=round(similarity, 4),
                        summary=f"{before.title} maddesinin metni %{round((1 - similarity) * 100)} oranında değişti.",
                    )
                )
            else:
                unchanged.append(clause_type)
            if set(before.risk_tags) != set(after.risk_tags) or similarity < 0.92:
                risk_changes.append(
                    RiskChange(
                        clause_type=clause_type,
                        before_tags=before.risk_tags,
                        after_tags=after.risk_tags,
                        direction="CHANGED" if similarity < 0.92 else "STABLE",
                    )
                )

        new_obligations = self._extract_new_sentences(comparison.clauses, base.clauses, ("yükümlü", "zorundadır", "taahhüt eder"))
        new_rights = self._extract_new_sentences(comparison.clauses, base.clauses, ("hak sahibi", "hakkına sahiptir", "talep edebilir"))
        summary = (
            f"{len(added)} madde eklendi, {len(removed)} madde kaldırıldı, "
            f"{len(modified)} madde değiştirildi."
        )
        return ContractComparisonResponse(
            base_contract_id=request.base_contract_id,
            comparison_contract_id=request.comparison_contract_id,
            added_clauses=sorted(added, key=lambda item: item.clause_type.value),
            removed_clauses=sorted(removed, key=lambda item: item.clause_type.value),
            modified_clauses=sorted(modified, key=lambda item: item.clause_type.value),
            unchanged_clauses=sorted(unchanged, key=lambda item: item.value),
            risk_changes=risk_changes,
            new_obligations=new_obligations,
            new_rights=new_rights,
            summary=summary,
        )

    @staticmethod
    def _best_by_type(clauses: list[DetectedClause]) -> dict[ClauseType, DetectedClause]:
        result: dict[ClauseType, DetectedClause] = {}
        for clause in clauses:
            current = result.get(clause.clause_type)
            if not current or clause.confidence > current.confidence:
                result[clause.clause_type] = clause
        return result

    @staticmethod
    def _extract_new_sentences(
        after: list[DetectedClause],
        before: list[DetectedClause],
        markers: tuple[str, ...],
    ) -> list[str]:
        before_text = " ".join(clause.text.casefold() for clause in before)
        sentences: list[str] = []
        for clause in after:
            for sentence in re.split(r"(?<=[.!?])\s+", clause.text):
                normalized = sentence.casefold().strip()
                if normalized and any(marker in normalized for marker in markers) and normalized not in before_text:
                    sentences.append(sentence.strip())
        return list(dict.fromkeys(sentences))[:10]

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.casefold()).strip()
