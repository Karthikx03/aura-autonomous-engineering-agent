"""Anthropic provider backed by ``anthropic.AsyncAnthropic``.

Anthropic's Messages API takes system prompts separately from the
user/assistant turn history and has no native JSON mode, so when
``json_mode`` is requested we append an explicit instruction to the system
prompt asking the model to return raw JSON only.
"""
from __future__ import annotations

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage

_JSON_INSTRUCTION = (
    "You must respond with raw JSON only - no markdown code fences, no "
    "prose before or after the JSON object."
)


class _Sentinel:
    __slots__ = ()


_NO_SYSTEM_PROMPT = _Sentinel()


class AnthropicProvider(LLMProvider):
    name = "anthropic"

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
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        system_parts = [m.content for m in messages if m.role == "system"]
        if json_mode:
            system_parts.append(_JSON_INSTRUCTION)
        system_prompt = "\n\n".join(system_parts) if system_parts else _NO_SYSTEM_PROMPT

        turn_messages = [
            {"role": m.role, "content": m.content} for m in messages if m.role in ("user", "assistant")
        ]
        if not turn_messages:
            turn_messages = [{"role": "user", "content": ""}]

        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=turn_messages,
        )
        if system_prompt is not _NO_SYSTEM_PROMPT:
            kwargs["system"] = system_prompt

        response = await client.messages.create(**kwargs)

        content = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        usage = getattr(response, "usage", None)
        return LLMResponse(
            content=content,
            model=getattr(response, "model", self.model) or self.model,
            provider=self.name,
            usage=LLMUsage(
                prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
                completion_tokens=getattr(usage, "output_tokens", 0) or 0,
            ),
            raw=response,
        )
