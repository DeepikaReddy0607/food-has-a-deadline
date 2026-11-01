import logging
import time
from typing import Optional, List, Dict, Any, Union
from google import genai
from google.genai import types, errors

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiError(Exception):
    """Base exception for Gemini provider errors."""
    pass


class GeminiUnavailableError(GeminiError):
    """Raised when Gemini service is unreachable, disabled, or encountering server errors."""
    pass


class GeminiQuotaExceededError(GeminiError):
    """Raised when Gemini quota or rate limits (HTTP 429) are exhausted."""
    pass


class GeminiProvider:
    """
    Encapsulates interaction with the Google Gen AI SDK (`google-genai`).
    Provides strict error normalization, rate-limit detection, and resilient recovery.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-2.5-flash"
        self._client: Optional[genai.Client] = None

        if self.api_key and self.api_key.strip():
            try:
                self._client = genai.Client(api_key=self.api_key.strip())
            except Exception as e:
                logger.warning("Failed to initialize Google Gen AI Client: %s", e)
                self._client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key or not self.api_key.strip():
                raise GeminiUnavailableError("GEMINI_API_KEY is not configured in environment.")
            self._client = genai.Client(api_key=self.api_key.strip())
        return self._client

    def is_available(self) -> bool:
        """
        Returns True if an API key is configured.
        """
        return bool(self.api_key and self.api_key.strip())

    def generate_chat_turn(
        self,
        contents: List[types.Content],
        tools: Optional[List[types.Tool]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
    ) -> types.GenerateContentResponse:
        """
        Executes a single generate_content call against the Gemini model.
        Normalizes HTTP 429, timeouts, and server errors into typed exceptions.
        """
        if not self.is_available():
            raise GeminiUnavailableError("Gemini API key is not configured.")

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools,
            temperature=temperature,
        )

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
                return response
            except errors.APIError as e:
                status_code = getattr(e, "code", None)
                msg = str(e).lower()

                # HTTP 429 / RESOURCE_EXHAUSTED: Do NOT retry in a loop
                if status_code == 429 or "resource_exhausted" in msg or "quota" in msg:
                    logger.warning("Gemini API rate limit or quota exceeded (429): %s", e)
                    raise GeminiQuotaExceededError(f"Gemini quota exceeded: {e}") from e

                # 5xx Server Errors: Allow bounded retry
                if status_code and 500 <= status_code < 600 and attempt < max_retries:
                    wait_sec = 0.5 * (2 ** attempt)
                    logger.warning("Transient Gemini server error (%d), retrying in %.1fs...", status_code, wait_sec)
                    time.sleep(wait_sec)
                    continue

                logger.error("Gemini API error (%s): %s", status_code, e)
                raise GeminiUnavailableError(f"Gemini API error ({status_code}): {e}") from e
            except Exception as e:
                msg = str(e).lower()
                if "429" in msg or "quota" in msg or "resource_exhausted" in msg:
                    raise GeminiQuotaExceededError(f"Gemini quota exceeded: {e}") from e
                if attempt < max_retries and ("timeout" in msg or "connection" in msg):
                    wait_sec = 0.5 * (2 ** attempt)
                    logger.warning("Network timeout contacting Gemini, retrying in %.1fs...", wait_sec)
                    time.sleep(wait_sec)
                    continue
                logger.error("Unexpected error contacting Gemini: %s", e)
                raise GeminiUnavailableError(f"Gemini service unavailable: {e}") from e
