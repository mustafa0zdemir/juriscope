import logging
import socket

from app.config.settings import settings
from app.core.exceptions import LLMConfigurationException, LLMUnavailableException
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, client=None) -> None:
        self.model_name = settings.gemini_model
        self._client = client

        if not settings.gemini_api_key:
            logger.error("GEMINI_API_KEY yapılandırılmamış")
            raise LLMConfigurationException(
                detail="Gemini API anahtarı yapılandırılmamış"
            )

    @property
    def client(self):
        if self._client is None:
            try:
                from google import genai
                from google.genai import types

                self._client = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options=types.HttpOptions(
                        timeout=int(settings.gemini_timeout_seconds * 1000)
                    ),
                )
            except ImportError:
                logger.exception("google-genai SDK yüklenemedi")
                raise LLMUnavailableException(
                    detail="Gemini SDK kullanılamıyor"
                ) from None
            except Exception:
                logger.exception("Gemini istemcisi oluşturulamadı")
                raise LLMUnavailableException(
                    detail="Gemini servisine bağlanılamadı"
                ) from None
        return self._client

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.gemini_api_key)

    def generate(self, prompt: str) -> str:
        try:
            client = self.client
            try:
                from google.genai import types

                generation_config = types.GenerateContentConfig(
                    max_output_tokens=settings.max_output_tokens,
                    temperature=settings.temperature,
                    top_p=settings.top_p,
                )
            except ImportError:
                if self._client is None:
                    raise
                generation_config = {
                    "max_output_tokens": settings.max_output_tokens,
                    "temperature": settings.temperature,
                    "top_p": settings.top_p,
                }

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=generation_config,
            )
            answer = response.text
            if not answer:
                raise LLMUnavailableException(
                    detail="Gemini boş bir cevap döndürdü"
                )
            return answer.strip()
        except LLMUnavailableException:
            raise
        except (TimeoutError, socket.timeout) as exc:
            logger.warning("Gemini isteği zaman aşımına uğradı")
            raise LLMUnavailableException(
                detail="Gemini isteği zaman aşımına uğradı"
            ) from exc
        except ImportError as exc:
            logger.exception("google-genai SDK yüklenemedi")
            raise LLMUnavailableException(
                detail="Gemini SDK kullanılamıyor"
            ) from exc
        except Exception as exc:
            if "timeout" in type(exc).__name__.lower():
                logger.warning("Gemini isteği zaman aşımına uğradı")
                raise LLMUnavailableException(
                    detail="Gemini isteği zaman aşımına uğradı"
                ) from exc
            logger.exception("Gemini API çağrısı başarısız oldu")
            raise LLMUnavailableException(
                detail="Gemini API erişilemiyor"
            ) from exc
