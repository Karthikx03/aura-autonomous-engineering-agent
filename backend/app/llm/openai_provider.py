"""OpenAI provider backed by ``openai.AsyncOpenAI``.

Kept import-safe with no API key configured (``is_configured()`` simply
returns ``False`` and ``factory.get_provider`` falls back to
``MockProvider``); the OpenAI SDK itself doesn't perform network calls at
construction time so this never crashes on import or instantiation.
"""
from __future__ import annotations

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        from openai import NOT_GIVEN, AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        payload = [{"role": m.role, "content": m.content} for m in messages]
        response = await client.chat.completions.create(
            model=self.model,
            messages=payload,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"} if json_mode else NOT_GIVEN,
        )
        choice = response.choices[0]
        content = choice.message.content or ""
        usage = response.usage
        return LLMResponse(
            content=content,
            model=response.model or self.model,
            provider=self.name,
            usage=LLMUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
            raw=response,
        )
