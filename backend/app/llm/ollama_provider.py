"""Ollama provider — talks to a local Ollama server over HTTP.

Ollama is local and optional, so ``is_configured()`` always returns
``True`` (there is no API key to check). If the server isn't actually
running, the HTTP call inside ``_complete`` raises, and ``LLMProvider.complete``
(in ``base.py``) normalizes that into an ``LLMProviderError`` — that's the
expected failure mode, not something this module should swallow.
"""
from __future__ import annotations

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_configured(self) -> bool:
        return True

    async def _complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        import httpx

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=120.0) as client:
            http_response = await client.post(f"{self.base_url}/api/chat", json=payload)
            http_response.raise_for_status()
            data = http_response.json()

        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0) or 0
        completion_tokens = data.get("eval_count", 0) or 0
        return LLMResponse(
            content=content,
            model=data.get("model", self.model) or self.model,
            provider=self.name,
            usage=LLMUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
            raw=data,
        )
