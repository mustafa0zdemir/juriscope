from enum import Enum


class AnalysisType(str, Enum):
    FULL = "full"


class RiskCategory(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def risk_category_for_score(score: int) -> RiskCategory:
    if score < 25:
        return RiskCategory.LOW
    if score < 50:
        return RiskCategory.MEDIUM
    if score < 75:
        return RiskCategory.HIGH
    return RiskCategory.CRITICAL
