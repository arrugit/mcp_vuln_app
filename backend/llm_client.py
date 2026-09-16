"""
LLM Client — HTTP client for local Ollama instance.

Provides a simple async interface to Ollama's /api/generate endpoint.
Uses only stdlib (urllib.request) — no external HTTP libraries required.

Configuration:
  VULNEX_OLLAMA_URL  — Ollama base URL (default: http://localhost:11434)
  VULNEX_OLLAMA_MODEL — model to use (default: llama3.2:3b)
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration via environment variables
OLLAMA_URL: str = os.getenv("VULNEX_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("VULNEX_OLLAMA_MODEL", "llama3.2:3b")


class LLMError(Exception):
    """Raised when the LLM request fails."""


class LLMClient:
    """
    Async HTTP client for Ollama's /api/generate endpoint.

    Sends prompts to the local Ollama instance and returns generated text.
    Uses urllib.request from stdlib to avoid adding HTTP library dependencies.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_URL,
        model: str = OLLAMA_MODEL,
    ) -> None:
        """
        Initialize the LLM client.

        Args:
            base_url: Ollama server base URL.
            model: Model name to use for generation.
        """
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt to send.
            system: Optional system prompt for context/instructions.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text response.

        Raises:
            LLMError: If the request fails or Ollama is unavailable.
        """
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system

        url = f"{self.base_url}/api/generate"
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            logger.info(
                "Calling Ollama: model=%s, prompt_length=%d",
                self.model,
                len(prompt),
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("response", "")

        except urllib.error.URLError as e:
            logger.error("Ollama connection failed: %s", e)
            raise LLMError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running and model '{self.model}' is pulled. "
                f"Error: {e}"
            ) from e
        except Exception as e:
            logger.error("Ollama request failed: %s", e)
            raise LLMError(f"LLM request failed: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if Ollama is reachable.

        Returns:
            True if Ollama is running, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False


# Module-level singleton
llm_client = LLMClient()
