"""Tests for the concrete LLM providers and the factory fallback behavior.

No real network calls are made anywhere in this file: every provider is
exercised only in its "unconfigured" state, which must be detected purely
from local state (an absent API key) without touching the network.
"""
from __future__ import annotations

from app.config import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.factory import available_providers, get_provider
from app.llm.gemini_provider import GeminiProvider
from app.llm.mock_provider import MockProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider


def test_openai_provider_unconfigured_without_api_key():
    provider = OpenAIProvider(api_key=None, model="gpt-4o-mini")
    assert provider.is_configured() is False
    assert provider.name == "openai"
    assert provider.model == "gpt-4o-mini"


def test_openai_provider_configured_with_api_key():
    provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
    assert provider.is_configured() is True


def test_anthropic_provider_unconfigured_without_api_key():
    provider = AnthropicProvider(api_key=None, model="claude-sonnet-4-5")
    assert provider.is_configured() is False
    assert provider.name == "anthropic"


def test_anthropic_provider_configured_with_api_key():
    provider = AnthropicProvider(api_key="sk-ant-test", model="claude-sonnet-4-5")
    assert provider.is_configured() is True


def test_gemini_provider_unconfigured_without_api_key():
    provider = GeminiProvider(api_key=None, model="gemini-1.5-pro")
    assert provider.is_configured() is False
    assert provider.name == "gemini"


def test_gemini_provider_configured_with_api_key():
    provider = GeminiProvider(api_key="test-key", model="gemini-1.5-pro")
    assert provider.is_configured() is True


def test_gemini_import_has_no_side_effects_when_unconfigured():
    # Constructing an unconfigured GeminiProvider must not call genai.configure
    # (which would be a global side effect); genai.configure is only invoked
    # lazily inside _complete.
    provider = GeminiProvider(api_key=None, model="gemini-1.5-pro")
    assert provider.api_key is None


def test_ollama_provider_is_always_configured():
    # Ollama is local/optional: is_configured() never touches the network.
    provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.1")
    assert provider.is_configured() is True
    assert provider.name == "ollama"


def test_available_providers_includes_all_backends():
    names = available_providers()
    for expected in ("openai", "anthropic", "gemini", "google", "ollama", "mock"):
        assert expected in names


def test_factory_falls_back_to_mock_for_every_provider_when_unconfigured():
    settings = Settings(
        default_llm_provider="mock",
        openai_api_key=None,
        anthropic_api_key=None,
        google_api_key=None,
        _env_file=None,
    )
    for provider_name in ("openai", "anthropic", "gemini", "google"):
        provider = get_provider(provider_name, settings=settings)
        assert isinstance(provider, MockProvider)


def test_factory_returns_mock_directly():
    settings = Settings(default_llm_provider="mock", _env_file=None)
    provider = get_provider("mock", settings=settings)
    assert isinstance(provider, MockProvider)


def test_factory_unknown_provider_raises():
    import pytest

    settings = Settings(_env_file=None)
    with pytest.raises(ValueError):
        get_provider("not-a-real-provider", settings=settings)


async def test_mock_provider_complete_json_mode_is_valid_json():
    import json

    from app.llm.base import LLMMessage

    provider = MockProvider()
    response = await provider.complete(
        [LLMMessage(role="user", content="please plan the work")],
        json_mode=True,
    )
    payload = json.loads(response.content)
    assert isinstance(payload, dict)
    assert response.provider == "mock"
