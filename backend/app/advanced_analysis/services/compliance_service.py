from sqlalchemy.orm import Session

from app.advanced_analysis.schemas import (
    ClauseType,
    ComplianceFinding,
    ComplianceReport,
    ComplianceStatus,
)
from app.advanced_analysis.services.clause_detection_service import ClauseDetectionService


LAW_REQUIREMENTS: dict[str, tuple[ClauseType, ...]] = {
    "Türk Borçlar Kanunu": (ClauseType.TERMINATION, ClauseType.PENALTY, ClauseType.FORCE_MAJEURE),
    "Türk Ticaret Kanunu": (ClauseType.PAYMENT, ClauseType.DELIVERY, ClauseType.INTELLECTUAL_PROPERTY),
    "KVKK": (ClauseType.KVKK, ClauseType.CONFIDENTIALITY),
    "İş Kanunu": (ClauseType.TERMINATION, ClauseType.NON_COMPETE, ClauseType.DURATION),
}


class ComplianceService:
    def __init__(self, clause_service: ClauseDetectionService | None = None) -> None:
        self.clause_service = clause_service or ClauseDetectionService()

    def check(self, db: Session, user_id: int, contract_id: int) -> ComplianceReport:
        clause_result = self.clause_service.detect(db, user_id, contract_id)
        detected = set(clause_result.detected_types)
        findings: list[ComplianceFinding] = []
        ratios: list[float] = []
        for law, required in LAW_REQUIREMENTS.items():
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
        score = round((sum(ratios) / len(ratios)) * 100)
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
