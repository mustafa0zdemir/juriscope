import json

from pydantic import ValidationError

from app.legal_analysis.schemas.analysis import ParsedAnalysisResponse


class AnalysisResponseParseError(ValueError):
    """LLM yanıtı analiz sözleşmesine uymadığında yükseltilir."""


class AnalysisResponseParser:
    def parse(self, response: str) -> ParsedAnalysisResponse:
        try:
            payload = json.loads(self._clean_json(response))
            return ParsedAnalysisResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise AnalysisResponseParseError("Gemini geçerli analiz JSON'u döndürmedi") from exc

    @staticmethod
    def _clean_json(response: str) -> str:
        content = response.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else ""
            if content.endswith("```"):
                content = content[:-3]
        return content.strip()
