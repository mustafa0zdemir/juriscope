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
        detected: dict[ClauseType, DetectedClause] = {}
        for chunk in chunks:
            normalized = self._normalize(chunk.text)
            for clause_type, rule in CLAUSE_RULES.items():
                matches = [
                    keyword
                    for keyword in rule.keywords
                    if self._contains_keyword(normalized, keyword)
                ]
                if not matches:
                    continue
                if clause_type is ClauseType.PAYMENT and not self._is_payment_clause(normalized, matches):
                    continue
                heading_match = self._has_heading(chunk.text, rule.title)
                confidence = min(0.95, 0.5 + (0.12 * len(matches)) + (0.15 if heading_match else 0))
                candidate = DetectedClause(
                    clause_type=clause_type,
                    title=rule.title,
                    contract_id=chunk.contract_id,
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text=self._extract_snippet(chunk.text, matches),
                    confidence=confidence,
                    matched_keywords=matches,
                    risk_tags=list(rule.risk_tags),
                )
                current = detected.get(clause_type)
                if current is None or candidate.confidence > current.confidence:
                    detected[clause_type] = candidate
        return sorted(detected.values(), key=lambda clause: (clause.chunk_index, clause.clause_type.value))

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.casefold()).strip()

    @classmethod
    def _contains_keyword(cls, normalized_text: str, keyword: str) -> bool:
        normalized_keyword = cls._normalize(keyword)
        return bool(re.search(rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)", normalized_text))

    @staticmethod
    def _has_heading(text: str, title: str) -> bool:
        return bool(re.search(rf"(?im)^\s*(?:madde\s+)?\d*[.):-]?\s*{re.escape(title)}\b", text))

    @classmethod
    def _is_payment_clause(cls, normalized_text: str, matches: list[str]) -> bool:
        if any(keyword in {"ödeme", "fatura"} for keyword in matches):
            return True
        return bool(re.search(r"(?<!\w)(?:bedel|ücret)(?!\w).{0,100}(?:öden|tahsil|vade)", normalized_text))

    @classmethod
    def _extract_snippet(cls, text: str, matches: list[str], radius: int = 320) -> str:
        normalized_text = text.casefold()
        positions = [normalized_text.find(keyword.casefold()) for keyword in matches]
        position = min(index for index in positions if index >= 0)
        start = max(0, position - radius)
        end = min(len(text), position + radius)
        if start:
            next_space = text.find(" ", start)
            start = next_space + 1 if next_space >= 0 else start
        if end < len(text):
            previous_space = text.rfind(" ", start, end)
            end = previous_space if previous_space > start else end
        snippet = cls._redact_sensitive_data(re.sub(r"\s+", " ", text[start:end]).strip())
        return f"{'…' if start else ''}{snippet}{'…' if end < len(text) else ''}"

    @staticmethod
    def _redact_sensitive_data(text: str) -> str:
        redacted = re.sub(
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
            "[E-POSTA GİZLENDİ]",
            text,
        )
        redacted = re.sub(
            r"(?i)(telefon\s*:\s*)\+?[\d\s()/-]{7,}",
            r"\1[TELEFON GİZLENDİ] ",
            redacted,
        )
        redacted = re.sub(
            r"(?i)((?:teslimat|fatura) adresi\s*:\s*).*?(?=\s+(?:telefon|e-?posta|teslim şekli|teslim edilecek kişi|fatura adresi)\s*:|$)",
            r"\1[ADRES GİZLENDİ]",
            redacted,
        )
        return re.sub(
            r"(?i)(teslim edilecek kişi\s*:\s*).*?(?=\s+(?:telefon|e-?posta|fatura adresi|teslim şekli)\s*:|$)",
            r"\1[KİŞİ GİZLENDİ]",
            redacted,
        )
