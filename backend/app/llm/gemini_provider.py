import logging
import socket
from collections.abc import Iterator
from typing import Any

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
        return self._generate(prompt, self._generation_config(), self.model_name)

    def generate_json(self, prompt: str, response_schema: Any) -> str:
        return self._generate(
            prompt,
            self._generation_config(
                max_output_tokens=settings.analysis_max_output_tokens,
                response_schema=response_schema,
            ),
            settings.gemini_analysis_model,
        )

    def _generate(self, prompt: str, generation_config: Any, model_name: str) -> str:
        try:
            client = self.client
            response = client.models.generate_content(
                model=model_name,
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
            error_text = f"{type(exc).__name__} {exc}".lower()
            if "timeout" in error_text or "deadline_exceeded" in error_text:
                logger.warning("Gemini isteği zaman aşımına uğradı")
                raise LLMUnavailableException(
                    detail="Gemini isteği zaman aşımına uğradı"
                ) from exc
            logger.exception("Gemini API çağrısı başarısız oldu")
            raise LLMUnavailableException(
                detail="Gemini API erişilemiyor"
            ) from exc

    def _generation_config(
        self,
        max_output_tokens: int | None = None,
        response_schema: Any | None = None,
    ):
        output_tokens = max_output_tokens or settings.max_output_tokens
        try:
            from google.genai import types

            return types.GenerateContentConfig(
                max_output_tokens=output_tokens,
                temperature=settings.temperature,
                top_p=settings.top_p,
                response_mime_type="application/json" if response_schema else None,
                response_schema=response_schema,
            )
        except ImportError:
            if self._client is None:
                raise
            config = {
                "max_output_tokens": output_tokens,
                "temperature": settings.temperature,
                "top_p": settings.top_p,
            }
            if response_schema:
                config["response_mime_type"] = "application/json"
                config["response_schema"] = response_schema
            return config

    def generate_stream(self, prompt: str) -> Iterator[str]:
        try:
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=self._generation_config(),
            )
            for response in response_stream:
                text = response.text or ""
                if text:
                    yield text
        except LLMUnavailableException:
            raise
        except (TimeoutError, socket.timeout) as exc:
            logger.warning("Gemini streaming isteği zaman aşımına uğradı")
            raise LLMUnavailableException(
                detail="Gemini streaming isteği zaman aşımına uğradı"
            ) from exc
        except Exception as exc:
            if "timeout" in type(exc).__name__.lower():
                logger.warning("Gemini streaming isteği zaman aşımına uğradı")
                raise LLMUnavailableException(
                    detail="Gemini streaming isteği zaman aşımına uğradı"
                ) from exc
            logger.exception("Gemini streaming çağrısı başarısız oldu")
            raise LLMUnavailableException(
                detail="Gemini streaming servisine erişilemiyor"
            ) from exc
