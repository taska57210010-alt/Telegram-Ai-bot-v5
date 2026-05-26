"""
Services layer for API calls and business logic.
Handles OpenRouter AI calls and payment processing.
"""

import logging
from typing import Optional

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import config

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Custom exception for OpenRouter API errors."""

    pass


class AIService:
    """Service for interacting with OpenRouter API."""

    def __init__(self) -> None:
        """Initialize AI service with reusable HTTP client."""
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(timeout=config.OPENROUTER_TIMEOUT)
        logger.info("AI Service initialized")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            logger.info("AI Service closed")

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raise if not initialized."""
        if not self._client:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")
        return self._client

    async def _call_openrouter_with_retry(
        self,
        model_name: str,
        messages: list,
    ) -> str:
        """
        Internal method to call OpenRouter API.

        Uses tenacity for exponential backoff retry logic.

        Args:
            model_name: Full model name
            messages: Message list

        Returns:
            AI response text

        Raises:
            OpenRouterError: If API call fails
        """
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        retry_strategy = AsyncRetrying(
            retry=retry_if_exception_type(
                (httpx.TimeoutException, httpx.HTTPStatusError)
            ),
            stop=stop_after_attempt(config.MAX_RETRIES),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )

        async for attempt in retry_strategy:
            with attempt:
                try:
                    logger.debug(
                        f"OpenRouter API call (attempt {attempt.retry_state.attempt_number}/{config.MAX_RETRIES}): "
                        f"model={model_name}"
                    )
                    response = await self.client.post(
                        f"{config.OPENROUTER_URL}/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=config.OPENROUTER_TIMEOUT,
                    )
                    response.raise_for_status()

                    data = response.json()

                    if "choices" not in data or not data["choices"]:
                        raise OpenRouterError("No choices in OpenRouter response")

                    result = data["choices"][0]["message"]["content"].strip()
                    logger.info(
                        f"OpenRouter API call successful (attempt {attempt.retry_state.attempt_number})"
                    )
                    return result

                except httpx.TimeoutException as e:
                    logger.warning(
                        f"OpenRouter timeout on attempt {attempt.retry_state.attempt_number}/{config.MAX_RETRIES}",
                        exc_info=True,
                    )
                    raise

                except httpx.HTTPStatusError as e:
                    status_code = e.response.status_code
                    if status_code == 429:  # Rate limit
                        logger.warning(
                            f"OpenRouter rate limit (429) on attempt {attempt.retry_state.attempt_number}/{config.MAX_RETRIES}",
                            exc_info=True,
                        )
                        raise
                    elif status_code >= 500:  # Server error
                        logger.warning(
                            f"OpenRouter server error ({status_code}) on attempt {attempt.retry_state.attempt_number}/{config.MAX_RETRIES}",
                            exc_info=True,
                        )
                        raise
                    else:
                        logger.exception(
                            f"OpenRouter client error: {status_code} - {e}"
                        )
                        raise OpenRouterError(f"OpenRouter API error: {status_code}") from e

                except Exception as e:
                    logger.exception(f"Unexpected OpenRouter error: {e}")
                    raise OpenRouterError(f"Failed to call OpenRouter: {str(e)}") from e

    async def call_openrouter(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Call OpenRouter API with exponential backoff retry logic.

        Args:
            prompt: User prompt/question
            model: Model identifier (must be valid key from config.AVAILABLE_MODELS)
            system_prompt: Optional system prompt for context

        Returns:
            AI response text

        Raises:
            OpenRouterError: If API call fails after retries
            ValueError: If model is invalid
        """
        # Validate model
        try:
            model_name = config.get_model_by_key(model)
        except ValueError as e:
            logger.exception(f"Invalid model selection: {model}")
            raise

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            return await self._call_openrouter_with_retry(model_name, messages)
        except OpenRouterError:
            raise
        except Exception as e:
            logger.exception(f"OpenRouter call failed: {e}")
            raise OpenRouterError(f"OpenRouter call failed: {str(e)}") from e

    async def get_available_models(self) -> dict:
        """Get list of available models."""
        return config.AVAILABLE_MODELS


class PaymentService:
    """Service for handling Telegram Stars payments."""

    @staticmethod
    def validate_payment_payload(payload: str) -> bool:
        """
        Validate payment payload format.

        Args:
            payload: Payment payload string

        Returns:
            True if valid format
        """
        if not payload or not isinstance(payload, str):
            return False

        parts = payload.split("_")
        if len(parts) != 2 or parts[0] != "stars":
            return False

        try:
            int(parts[1])
            return True
        except ValueError:
            return False

    @staticmethod
    def extract_stars_amount(payload: str) -> Optional[int]:
        """
        Extract stars amount from payment payload.

        Args:
            payload: Payment payload string

        Returns:
            Stars amount or None if invalid
        """
        if not PaymentService.validate_payment_payload(payload):
            return None

        try:
            return int(payload.split("_")[1])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def get_questions_for_stars(stars: int) -> int:
        """
        Calculate questions for stars amount.

        Args:
            stars: Number of stars

        Returns:
            Number of questions
        """
        return stars * config.QUESTIONS_PER_STAR
