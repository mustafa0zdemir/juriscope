import re

from app.trustworthy_rag.schemas import CitationCoverage


class CitationCoverageValidator:
    CITATION_PATTERN = re.compile(
        r"\[Kaynak\s+(\d+)\]|[\"']citation[\"']\s*:\s*(\d+)",
        flags=re.IGNORECASE,
    )

    def validate(self, answer: str, available_citations: int) -> CitationCoverage:
        claims = self._claims(answer)
        supported = sum(self._has_valid_citation(claim, available_citations) for claim in claims)
        total = len(claims)
        coverage = round((supported / total) * 100, 2) if total else 0.0
        return CitationCoverage(
            total_claims=total,
            supported_claims=supported,
            unsupported_claims=total - supported,
            coverage_percent=coverage,
        )

    @staticmethod
    def _claims(answer: str) -> list[str]:
        return [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+|\n+", answer.strip())
            if len(part.strip()) >= 15
        ]

    def _has_valid_citation(self, claim: str, available_citations: int) -> bool:
        for match in self.CITATION_PATTERN.finditer(claim):
            citation = int(match.group(1) or match.group(2))
            if 1 <= citation <= available_citations:
                return True
        return False
