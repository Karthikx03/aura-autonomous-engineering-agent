"""Provider factory.

``get_provider`` is the single place that decides which concrete
``LLMProvider`` implementation to instantiate. New providers register
themselves in ``_PROVIDERS`` — nothing else in the codebase should
``import`` a concrete provider class directly (agents and the orchestrator
depend only on ``app.llm.base.LLMProvider``).
"""
from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockProvider


def _load_openai(settings: Settings) -> LLMProvider:
    from app.llm.openai_provider import OpenAIProvider

    return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)


def _load_anthropic(settings: Settings) -> LLMProvider:
    from app.llm.anthropic_provider import AnthropicProvider

    return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)


def _load_gemini(settings: Settings) -> LLMProvider:
    from app.llm.gemini_provider import GeminiProvider

    return GeminiProvider(api_key=settings.google_api_key, model=settings.google_model)


def _load_ollama(settings: Settings) -> LLMProvider:
    from app.llm.ollama_provider import OllamaProvider

    return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)


_PROVIDERS = {
    "openai": _load_openai,
    "anthropic": _load_anthropic,
    "gemini": _load_gemini,
    "google": _load_gemini,
    "ollama": _load_ollama,
    "mock": lambda settings: MockProvider(),
}


def available_providers() -> list[str]:
    return sorted(_PROVIDERS.keys())


def get_provider(name: str | None = None, settings: Settings | None = None) -> LLMProvider:
    """Instantiate the requested provider, falling back to MockProvider.

    Falling back (rather than raising) keeps the orchestrator, tests, and
    demo mode runnable with zero configured API keys, which matters for a
    project that must be reproducible in CI without secrets.
    """
    settings = settings or get_settings()
    provider_name = (name or settings.default_llm_provider or "mock").lower()
    loader = _PROVIDERS.get(provider_name)
    if loader is None:
        raise ValueError(f"Unknown LLM provider '{provider_name}'. Available: {available_providers()}")
    try:
        provider = loader(settings)
    except Exception:
        return MockProvider()
    if not provider.is_configured():
        return MockProvider()
    return provider
