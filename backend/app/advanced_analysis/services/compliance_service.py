import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.advanced_analysis.schemas import (
    ClauseType,
    ComplianceFinding,
    ComplianceReport,
    ComplianceStatus,
)
from app.advanced_analysis.services.clause_detection_service import ClauseDetectionService
from app.repositories.document_chunk_repository import DocumentChunkRepository


@dataclass(frozen=True)
class ComplianceRule:
    required_clauses: tuple[ClauseType, ...]
    applicability_markers: tuple[str, ...] = ()


LAW_REQUIREMENTS: dict[str, ComplianceRule] = {
    "Türk Borçlar Kanunu": ComplianceRule(
        (ClauseType.TERMINATION, ClauseType.PENALTY, ClauseType.FORCE_MAJEURE)
    ),
    "Türk Ticaret Kanunu": ComplianceRule(
        (ClauseType.PAYMENT, ClauseType.DELIVERY, ClauseType.INTELLECTUAL_PROPERTY),
        ("tacir", "ticari işletme", "şirket", "satıcı", "alıcı"),
    ),
    "6698 Sayılı Kişisel Verilerin Korunması Kanunu": ComplianceRule(
        (ClauseType.KVKK, ClauseType.CONFIDENTIALITY),
        ("kişisel veri", "veri sorumlusu", "açık rıza", "gizlilik"),
    ),
    "4857 Sayılı İş Kanunu": ComplianceRule(
        (ClauseType.TERMINATION, ClauseType.NON_COMPETE, ClauseType.DURATION),
        ("işçi", "işveren", "iş sözleşmesi"),
    ),
    "6502 Sayılı Tüketicinin Korunması Hakkında Kanun": ComplianceRule(
        (ClauseType.PAYMENT, ClauseType.DELIVERY, ClauseType.TERMINATION),
        ("tüketici", "mesafeli sözleşme", "6502", "ön bilgilendirme", "cayma hakkı"),
    ),
}


class ComplianceService:
    def __init__(self, clause_service: ClauseDetectionService | None = None) -> None:
        self.clause_service = clause_service or ClauseDetectionService()

    def check(self, db: Session, user_id: int, contract_id: int) -> ComplianceReport:
        clause_result = self.clause_service.detect(db, user_id, contract_id)
        detected = set(clause_result.detected_types)
        corpus = " ".join(
            chunk.text.casefold()
            for chunk in DocumentChunkRepository(db).list_by_contract_id(contract_id)
        )
        findings: list[ComplianceFinding] = []
        ratios: list[float] = []
        for law, rule in LAW_REQUIREMENTS.items():
            required = rule.required_clauses
            if not self._is_applicable(law, rule, corpus):
                findings.append(
                    ComplianceFinding(
                        law=law,
                        status=ComplianceStatus.NOT_APPLICABLE,
                        required_clauses=list(required),
                        detected_clauses=[],
                        missing_clauses=[],
                        issues=[],
                        recommendation="Sözleşme içeriğinde bu mevzuatın uygulanmasını gerektiren bir taraf veya ilişki tespit edilmedi.",
                    )
                )
                continue
            present = [clause_type for clause_type in required if clause_type in detected]
            missing = [clause_type for clause_type in required if clause_type not in detected]
            ratio = len(present) / len(required)
            ratios.append(ratio)
            status = self._status(ratio)
            findings.append(
                ComplianceFinding(
                    law=law,
                    status=status,
                    required_clauses=list(required),
                    detected_clauses=present,
                    missing_clauses=missing,
                    issues=[f"{clause_type.value} maddesi tespit edilemedi." for clause_type in missing],
                    recommendation=(
                        "İlgili hükümler tespit edildi; kapsam ve uygulanabilirlik hukuk uzmanı tarafından doğrulanmalıdır."
                        if not missing
                        else "Eksik görünen hükümler sözleşme türüne göre eklenmeli ve hukuk uzmanı tarafından incelenmelidir."
                    ),
                )
            )
        score = round((sum(ratios) / len(ratios)) * 100) if ratios else 0
        risk_tags = sorted(
            {tag for clause in clause_result.clauses for tag in clause.risk_tags},
            key=lambda tag: tag.value,
        )
        return ComplianceReport(
            contract_id=contract_id,
            compliance_score=score,
            status=self._status(score / 100),
            findings=findings,
            risk_tags=risk_tags,
            disclaimer="Bu otomatik kontrol hukuki görüş değildir; mevzuata uygunluk uzman incelemesi gerektirir.",
        )

    @staticmethod
    def _status(ratio: float) -> ComplianceStatus:
        if ratio >= 0.99:
            return ComplianceStatus.COMPLIANT
        if ratio > 0:
            return ComplianceStatus.PARTIAL
        return ComplianceStatus.NON_COMPLIANT

    @staticmethod
    def _is_applicable(law: str, rule: ComplianceRule, corpus: str) -> bool:
        if not rule.applicability_markers:
            return True
        if law == "4857 Sayılı İş Kanunu":
            return ComplianceService._contains_marker(corpus, "iş sözleşmesi") or (
                ComplianceService._contains_marker(corpus, "işçi")
                and ComplianceService._contains_marker(corpus, "işveren")
            )
        return any(
            ComplianceService._contains_marker(corpus, marker)
            for marker in rule.applicability_markers
        )

    @staticmethod
    def _contains_marker(corpus: str, marker: str) -> bool:
        return bool(re.search(rf"(?<!\w){re.escape(marker)}(?!\w)", corpus))
