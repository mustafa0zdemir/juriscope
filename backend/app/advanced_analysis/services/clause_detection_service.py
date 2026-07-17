import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.advanced_analysis.schemas import ClauseListResponse, ClauseType, DetectedClause, RiskTag
from app.advanced_analysis.services.base import ContractAnalysisAccess
from app.models.document_chunk import DocumentChunk
from app.repositories.document_chunk_repository import DocumentChunkRepository


@dataclass(frozen=True)
class ClauseRule:
    title: str
    keywords: tuple[str, ...]
    risk_tags: tuple[RiskTag, ...]


CLAUSE_RULES: dict[ClauseType, ClauseRule] = {
    ClauseType.CONFIDENTIALITY: ClauseRule("Gizlilik", ("gizlilik", "gizli bilgi", "sır saklama"), (RiskTag.PRIVACY, RiskTag.COMMERCIAL)),
    ClauseType.TERMINATION: ClauseRule("Fesih", ("fesih", "sözleşmenin sona ermesi", "ihbar süresi"), (RiskTag.LEGAL, RiskTag.COMMERCIAL)),
    ClauseType.PENALTY: ClauseRule("Cezai Şart", ("cezai şart", "ceza koşulu", "gecikme cezası"), (RiskTag.FINANCIAL, RiskTag.LEGAL)),
    ClauseType.FORCE_MAJEURE: ClauseRule("Mücbir Sebep", ("mücbir sebep", "mücbir neden", "beklenmeyen hal"), (RiskTag.LEGAL, RiskTag.COMMERCIAL)),
    ClauseType.ARBITRATION: ClauseRule("Tahkim", ("tahkim", "hakem heyeti", "hakem kurulu"), (RiskTag.LEGAL,)),
    ClauseType.JURISDICTION: ClauseRule("Yetkili Mahkeme", ("yetkili mahkeme", "mahkemeleri ve icra daireleri", "yargı yeri"), (RiskTag.LEGAL,)),
    ClauseType.PAYMENT: ClauseRule("Ödeme", ("ödeme", "ücret", "fatura", "bedel"), (RiskTag.FINANCIAL, RiskTag.COMMERCIAL)),
    ClauseType.DURATION: ClauseRule("Süre", ("sözleşme süresi", "yürürlük tarihi", "geçerlilik süresi", "süre uzatımı"), (RiskTag.LEGAL, RiskTag.COMMERCIAL)),
    ClauseType.DELIVERY: ClauseRule("Teslim", ("teslim", "teslimat", "ifa tarihi"), (RiskTag.COMMERCIAL, RiskTag.FINANCIAL)),
    ClauseType.KVKK: ClauseRule("KVKK", ("kvkk", "kişisel veri", "veri sorumlusu", "açık rıza"), (RiskTag.PRIVACY, RiskTag.LEGAL)),
    ClauseType.NON_COMPETE: ClauseRule("Rekabet Yasağı", ("rekabet yasağı", "rekabet etmeme", "rakip işletme"), (RiskTag.EMPLOYMENT, RiskTag.COMMERCIAL)),
    ClauseType.INTELLECTUAL_PROPERTY: ClauseRule("Fikri Mülkiyet", ("fikri mülkiyet", "telif hakkı", "marka hakkı", "patent", "lisans"), (RiskTag.LEGAL, RiskTag.COMMERCIAL)),
}


class ClauseDetectionService:
    def detect(self, db: Session, user_id: int, contract_id: int) -> ClauseListResponse:
        ContractAnalysisAccess.require_ready_contract(db, contract_id, user_id)
        chunks = DocumentChunkRepository(db).list_by_contract_id(contract_id)
        clauses = self.detect_chunks(chunks)
        detected = list(dict.fromkeys(clause.clause_type for clause in clauses))
        return ClauseListResponse(
            contract_id=contract_id,
            clauses=clauses,
            detected_types=detected,
            missing_types=[clause_type for clause_type in ClauseType if clause_type not in detected],
        )

    def detect_chunks(self, chunks: list[DocumentChunk]) -> list[DetectedClause]:
        detected: list[DetectedClause] = []
        for chunk in chunks:
            normalized = self._normalize(chunk.text)
            for clause_type, rule in CLAUSE_RULES.items():
                matches = [keyword for keyword in rule.keywords if self._normalize(keyword) in normalized]
                if not matches:
                    continue
                confidence = min(1.0, 0.55 + (0.15 * len(matches)))
                detected.append(
                    DetectedClause(
                        clause_type=clause_type,
                        title=rule.title,
                        contract_id=chunk.contract_id,
                        chunk_id=chunk.id,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        text=chunk.text,
                        confidence=confidence,
                        matched_keywords=matches,
                        risk_tags=list(rule.risk_tags),
                    )
                )
        return sorted(detected, key=lambda clause: (clause.chunk_index, clause.clause_type.value))

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.casefold()).strip()
