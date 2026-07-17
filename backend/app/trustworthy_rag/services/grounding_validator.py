import re

from app.trustworthy_rag.schemas import GroundingLevel, GroundingResult


class GroundingValidator:
    def validate(self, answer: str, context: str, citation_count: int) -> GroundingResult:
        stripped = answer.strip()
        answer_empty = not stripped
        answer_too_short = 0 < len(stripped) < 40
        has_citations = bool(
            re.search(r"\[Kaynak\s+\d+\]|[\"']citation[\"']\s*:\s*\d+", stripped, re.IGNORECASE)
        )
        overlap = self._context_overlap(stripped, context)
        score = 100
        reasons: list[str] = []
        if answer_empty:
            score = 0
            reasons.append("Cevap boş.")
        if answer_too_short:
            score -= 25
            reasons.append("Cevap güvenilir değerlendirme için çok kısa.")
        if citation_count and not has_citations:
            score -= 30
            reasons.append("Cevapta doğrulanabilir kaynak referansı bulunmuyor.")
        if overlap < 0.15:
            score -= 35
            reasons.append("Cevabın context ile kelime örtüşmesi düşük.")
        elif overlap < 0.3:
            score -= 15
            reasons.append("Cevabın context ile kelime örtüşmesi sınırlı.")
        bounded = max(0, min(100, score))
        level = (
            GroundingLevel.GROUNDED
            if bounded >= 75
            else GroundingLevel.PARTIALLY_GROUNDED
            if bounded >= 45
            else GroundingLevel.LOW_GROUNDED
        )
        return GroundingResult(
            level=level,
            score=bounded,
            answer_empty=answer_empty,
            answer_too_short=answer_too_short,
            has_citations=has_citations,
            context_overlap=round(overlap, 4),
            reasons=reasons,
        )

    @staticmethod
    def _context_overlap(answer: str, context: str) -> float:
        answer_terms = set(re.findall(r"\b\w{4,}\b", answer.casefold()))
        if not answer_terms:
            return 0.0
        context_terms = set(re.findall(r"\b\w{4,}\b", context.casefold()))
        return len(answer_terms & context_terms) / len(answer_terms)
