"""Provider-agnostic LLM abstraction.

AURA never hard-codes itself around a single model vendor. Every concrete
provider (OpenAI, Anthropic, Gemini, Ollama, or the deterministic Mock used
in tests/CI) implements this same small interface, so the orchestrator and
every agent can be written once against ``LLMProvider`` and swapped freely
at runtime via ``factory.get_provider``.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from app.observability.logger import log_event

Role = Literal["system", "user", "assistant"]


@dataclass
class LLMMessage:
    role: Role
    content: str


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    raw: Any = None


class LLMProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a completion request."""


class LLMProvider(ABC):
    """Common interface every AURA LLM backend must implement."""

    name: str = "base"

    @abstractmethod
    async def _complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Provider-specific completion call. Not called directly."""

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Run a completion, timing and logging the call.

        This wraps ``_complete`` so every provider gets identical
        observability (latency, token usage, structured event log) for
        free, and so failures are normalized into ``LLMProviderError``.
        """
        started = time.perf_counter()
        try:
            response = await self._complete(
                messages, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive normalization
            raise LLMProviderError(f"{self.name} provider failed: {exc}") from exc
        latency = time.perf_counter() - started
        log_event(
            {
                "event": "llm_call",
                "provider": self.name,
                "model": response.model,
                "latency_seconds": latency,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }
        )
        return response

    def is_configured(self) -> bool:
        """Whether this provider has everything it needs (e.g. an API key)."""
        return True
