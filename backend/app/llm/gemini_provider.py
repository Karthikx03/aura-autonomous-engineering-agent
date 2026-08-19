"""Google Gemini provider backed by ``google.generativeai``.

``genai.configure`` is only invoked inside ``_complete`` (never at import
time) so importing this module, or instantiating an unconfigured
``GeminiProvider``, has no global side effects. Gemini's Python SDK models a
single flat prompt string rather than a structured chat history for
single-shot generation, so we flatten the ``LLMMessage`` list into one
role-prefixed prompt.
"""
from __future__ import annotations

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage


def _flatten(messages: list[LLMMessage]) -> str:
    parts = []
    for m in messages:
        prefix = {"system": "System", "user": "User", "assistant": "Assistant"}.get(m.role, m.role)
        parts.append(f"{prefix}: {m.content}")
    parts.append("Assistant:")
    return "\n\n".join(parts)


class GeminiProvider(LLMProvider):
    name = "gemini"

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
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        generation_config: dict = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        client = genai.GenerativeModel(model_name=self.model)
        prompt = _flatten(messages)
        response = await client.generate_content_async(prompt, generation_config=generation_config)

        content = response.text if getattr(response, "text", None) else ""
        usage_meta = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.name,
            usage=LLMUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
            raw=response,
        )
