"""Per-provider live tests: model discovery + a 1-token completion."""
from __future__ import annotations

import pytest

import ask_another.server as server

pytestmark = pytest.mark.integration


# Cheapest, fastest model per provider for completion smoke tests.
# Pinned to specific IDs to avoid silent drift to a more expensive default.
CHEAP_MODEL = {
    "openai": "openai/gpt-5-nano",
    "gemini": "gemini/gemini-2.5-flash",
    "openrouter": "openrouter/openai/gpt-5-nano",
}


def test_fetch_models_openai(openai_key: str) -> None:
    models = server._fetch_models("openai", openai_key)
    assert models, "OpenAI returned no models"
    assert any(m.startswith("openai/") for m in models)


def test_fetch_models_gemini(gemini_key: str) -> None:
    models = server._fetch_models("gemini", gemini_key)
    assert models, "Gemini returned no models"
    assert any(m.startswith("gemini/") for m in models)


def test_fetch_models_openrouter(openrouter_key: str) -> None:
    models = server._fetch_models("openrouter", openrouter_key, zdr=True)
    assert models, "OpenRouter returned no ZDR models"
    assert any(m.startswith("openrouter/") for m in models)


def test_no_provider_errors_after_clean_refresh(configured_providers: list[str]) -> None:
    """A refresh with valid keys leaves every provider healthy."""
    server._provider_errors.clear()
    server._model_cache.clear()
    server._refresh_provider_models()
    unhealthy = {p: e for p, e in server._provider_errors.items() if e}
    assert not unhealthy, f"Providers unhealthy after refresh: {unhealthy}"


@pytest.mark.parametrize("provider", ["openai", "gemini", "openrouter"])
def test_completion_returns_text(provider: str, request: pytest.FixtureRequest) -> None:
    """A minimal completion returns non-empty text.

    Don't pass temperature — gpt-5 family rejects anything other than 1, and
    we just want to confirm the call path works.
    """
    request.getfixturevalue(f"{provider}_key")
    model = CHEAP_MODEL[provider]
    out = server.completion(
        model=model,
        prompt="Reply with exactly the word: pong",
    )
    assert isinstance(out, str)
    assert out.strip(), f"{model} returned empty completion"
