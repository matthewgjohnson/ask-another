"""Tests for provider health validation."""

import ask_another.server as server


def test_healthy_provider_has_no_error(monkeypatch):
    """A provider whose fetch returns models has no error."""
    monkeypatch.setattr(server, "_provider_registry", {"openai": "sk-test"})
    monkeypatch.setattr(server, "_provider_errors", {})
    monkeypatch.setattr(server, "_model_cache", {})
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {})
    monkeypatch.setattr(
        server, "_fetch_models", lambda p, k, zdr=False: ["openai/gpt-5.2"]
    )
    server._refresh_provider_models()
    assert server._provider_errors.get("openai") is None


def test_unhealthy_provider_stores_error(monkeypatch):
    """A provider whose fetch raises stores the error message."""
    monkeypatch.setattr(server, "_provider_registry", {"gemini": "bad-key"})
    monkeypatch.setattr(server, "_provider_errors", {})
    monkeypatch.setattr(server, "_model_cache", {})
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {})

    def _fail(p, k, zdr=False):
        raise Exception("Google API key is required")

    monkeypatch.setattr(server, "_fetch_models", _fail)
    server._refresh_provider_models()
    assert server._provider_errors["gemini"] == "Google API key is required"


def test_empty_models_stores_error(monkeypatch):
    """A provider returning zero models is marked unhealthy."""
    monkeypatch.setattr(server, "_provider_registry", {"gemini": "sk-test"})
    monkeypatch.setattr(server, "_provider_errors", {})
    monkeypatch.setattr(server, "_model_cache", {})
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {})
    monkeypatch.setattr(server, "_fetch_models", lambda p, k, zdr=False: [])
    server._refresh_provider_models()
    assert server._provider_errors["gemini"] == "No models returned"


def test_get_models_skips_unhealthy_providers(monkeypatch):
    """_get_models excludes providers with errors."""
    monkeypatch.setattr(server, "_provider_registry", {
        "openai": "sk-good",
        "gemini": "bad-key",
    })
    monkeypatch.setattr(server, "_provider_errors", {
        "openai": None,
        "gemini": "Google API key is required",
    })
    monkeypatch.setattr(server, "_model_cache", {
        "openai": (["openai/gpt-5.2"], 9999999999.0),
    })
    monkeypatch.setattr(server, "_cache_ttl_minutes", 360)
    monkeypatch.setattr(server, "_zero_data_retention", True)

    models = server._get_models()
    assert "openai/gpt-5.2" in models
    assert not any(m.startswith("gemini/") for m in models)
