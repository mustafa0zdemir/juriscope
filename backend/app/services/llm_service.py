import logging
from collections.abc import Iterator
from typing import Any

from app.config.settings import settings
from app.core.exceptions import LLMConfigurationException, LLMUnavailableException
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider

    @property
    def model_name(self) -> str:
        if self._provider is not None:
            return getattr(self._provider, "model_name", settings.gemini_model)
        return settings.gemini_model

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = GeminiProvider()
        return self._provider

    def generate(self, prompt: str) -> str:
        try:
            return self.provider.generate(prompt)
        except (LLMConfigurationException, LLMUnavailableException):
            raise
        except (TimeoutError,):
            logger.warning("LLM isteği zaman aşımına uğradı")
            raise LLMUnavailableException(
                detail="LLM isteği zaman aşımına uğradı"
            ) from None
        except Exception:
            logger.exception("LLM cevabı oluşturulamadı")
            raise LLMUnavailableException(
                detail="LLM servisi kullanılamıyor"
            ) from None

    def generate_json(self, prompt: str, response_schema: Any) -> str:
        try:
            return self.provider.generate_json(prompt, response_schema)
        except (LLMConfigurationException, LLMUnavailableException):
            raise
        except TimeoutError:
            logger.warning("Yapılandırılmış LLM isteği zaman aşımına uğradı")
            raise LLMUnavailableException(
                detail="LLM isteği zaman aşımına uğradı"
            ) from None
        except Exception:
            logger.exception("Yapılandırılmış LLM cevabı oluşturulamadı")
            raise LLMUnavailableException(
                detail="LLM servisi kullanılamıyor"
            ) from None

    def generate_stream(self, prompt: str) -> Iterator[str]:
        try:
            yield from self.provider.generate_stream(prompt)
        except (LLMConfigurationException, LLMUnavailableException):
            raise
        except TimeoutError:
            logger.warning("LLM streaming isteği zaman aşımına uğradı")
            raise LLMUnavailableException(
                detail="LLM streaming isteği zaman aşımına uğradı"
            ) from None
        except Exception:
            logger.exception("LLM streaming cevabı oluşturulamadı")
            raise LLMUnavailableException(
                detail="LLM streaming servisi kullanılamıyor"
            ) from None
