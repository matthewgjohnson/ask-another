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


def test_build_instructions_excludes_unhealthy_favourites(monkeypatch):
    """Favourites from unhealthy providers are excluded from instructions."""
    monkeypatch.setattr(server, "_provider_registry", {
        "openai": "sk-good",
        "gemini": "bad-key",
    })
    monkeypatch.setattr(server, "_provider_errors", {
        "openai": None,
        "gemini": "API key invalid",
    })
    monkeypatch.setattr(server, "_annotations", {
        "openai/gpt-5.2": {
            "usage": {"call_count": 10, "last_used": "2026-03-12T00:00:00Z"},
            "annotations": {"note": "Fast"},
        },
        "gemini/gemini-3.1-pro": {
            "usage": {"call_count": 20, "last_used": "2026-03-12T00:00:00Z"},
            "annotations": {"note": "Long context"},
        },
    })
    instructions = server._build_instructions()
    assert "openai/gpt-5.2" in instructions
    assert "gemini/gemini-3.1-pro" not in instructions


def test_build_instructions_shows_unavailable_providers(monkeypatch):
    """Instructions include an Unavailable Providers section with error messages."""
    monkeypatch.setattr(server, "_provider_registry", {
        "openai": "sk-good",
        "gemini": "bad-key",
    })
    monkeypatch.setattr(server, "_provider_errors", {
        "openai": None,
        "gemini": "Google API key is required",
    })
    monkeypatch.setattr(server, "_annotations", {})
    instructions = server._build_instructions()
    assert "Unavailable Providers:" in instructions
    assert "gemini: Google API key is required" in instructions


def test_search_models_retries_unhealthy_provider(monkeypatch):
    """Searching for an unhealthy provider triggers a retry."""
    monkeypatch.setattr(server, "_provider_registry", {"gemini": "fixed-key"})
    monkeypatch.setattr(server, "_provider_errors", {
        "gemini": "API key invalid",
    })
    monkeypatch.setattr(server, "_model_cache", {})
    monkeypatch.setattr(server, "_cache_ttl_minutes", 360)
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {})

    # Retry succeeds
    monkeypatch.setattr(
        server, "_fetch_models", lambda p, k, zdr=False: ["gemini/gemini-3.1-pro"]
    )
    result = server.search_models(search="gemini")
    assert "gemini/gemini-3.1-pro" in result
    assert server._provider_errors.get("gemini") is None


def test_search_models_shows_error_on_retry_failure(monkeypatch):
    """If retry still fails, error message is shown in results."""
    monkeypatch.setattr(server, "_provider_registry", {"gemini": "bad-key"})
    monkeypatch.setattr(server, "_provider_errors", {
        "gemini": "API key invalid",
    })
    monkeypatch.setattr(server, "_model_cache", {})
    monkeypatch.setattr(server, "_cache_ttl_minutes", 360)
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {})

    def _fail(p, k, zdr=False):
        raise Exception("Still broken")

    monkeypatch.setattr(server, "_fetch_models", _fail)
    result = server.search_models(search="gemini")
    assert "gemini" in result
    assert "Still broken" in result


def test_full_flow_healthy_and_unhealthy(monkeypatch):
    """End-to-end: one healthy provider, one unhealthy — verify filtering everywhere."""
    monkeypatch.setattr(server, "_provider_registry", {
        "openai": "sk-good",
        "gemini": "bad-key",
    })
    monkeypatch.setattr(server, "_provider_errors", {})
    monkeypatch.setattr(server, "_model_cache", {})
    monkeypatch.setattr(server, "_cache_ttl_minutes", 360)
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {
        "openai/gpt-5.2": {
            "metadata": {"arena_elo": 1400},
            "usage": {"call_count": 10, "last_used": "2026-03-12T00:00:00Z"},
        },
        "gemini/gemini-3.1-pro": {
            "metadata": {"arena_elo": 1500},
            "usage": {"call_count": 20, "last_used": "2026-03-12T00:00:00Z"},
        },
    })

    def _mock_fetch(p, k, zdr=False):
        if p == "openai":
            return ["openai/gpt-5.2"]
        raise Exception("API key invalid")

    monkeypatch.setattr(server, "_fetch_models", _mock_fetch)

    # Startup refresh
    server._refresh_provider_models()

    # Models filtered
    models = server._get_models()
    assert "openai/gpt-5.2" in models
    assert not any(m.startswith("gemini/") for m in models)

    # Instructions filtered
    instructions = server._build_instructions()
    assert "openai/gpt-5.2" in instructions
    assert "gemini/gemini-3.1-pro" not in instructions
    assert "Unavailable Providers:" in instructions
    assert "gemini: API key invalid" in instructions


def test_generate_image_auth_error_marks_provider_unhealthy(monkeypatch):
    """An auth error during image generation marks the provider unhealthy."""
    monkeypatch.setattr(server, "_provider_registry", {"openai": "bad-key"})
    monkeypatch.setattr(server, "_provider_errors", {"openai": None})
    monkeypatch.setattr(server, "_model_cache", {
        "openai": (["openai/gpt-image-1"], 9999999999.0),
    })
    monkeypatch.setattr(server, "_cache_ttl_minutes", 360)
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {})
    monkeypatch.setattr(
        server, "_resolve_model",
        lambda m: ("openai/gpt-image-1", "bad-key"),
    )
    monkeypatch.setattr(
        server, "_get_models",
        lambda provider=None, *, zdr=None: ["openai/gpt-image-1"],
    )

    import litellm

    def _fail_auth(**kwargs):
        raise litellm.AuthenticationError(
            message="Invalid API key",
            llm_provider="openai",
            model="openai/gpt-image-1",
        )

    monkeypatch.setattr(litellm, "image_generation", _fail_auth)

    import pytest
    with pytest.raises(litellm.AuthenticationError):
        server.generate_image(model="openai/gpt-image-1", prompt="a cat")

    assert server._provider_errors["openai"] is not None
    assert "Authentication" in server._provider_errors["openai"]


def test_generate_image_native_auth_error_marks_provider_unhealthy(monkeypatch):
    """An auth error on the native image model completion path marks provider unhealthy."""
    monkeypatch.setattr(server, "_provider_registry", {"gemini": "bad-key"})
    monkeypatch.setattr(server, "_provider_errors", {"gemini": None})
    monkeypatch.setattr(server, "_model_cache", {
        "gemini": (["gemini/gemini-2.5-flash-image"], 9999999999.0),
    })
    monkeypatch.setattr(server, "_cache_ttl_minutes", 360)
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {})
    monkeypatch.setattr(
        server, "_resolve_model",
        lambda m: ("gemini/gemini-2.5-flash-image", "bad-key"),
    )
    monkeypatch.setattr(
        server, "_get_models",
        lambda provider=None, *, zdr=None: ["gemini/gemini-2.5-flash-image"],
    )

    import litellm

    def _fail_auth(**kwargs):
        raise litellm.AuthenticationError(
            message="API key invalid",
            llm_provider="gemini",
            model="gemini/gemini-2.5-flash-image",
        )

    monkeypatch.setattr(litellm, "completion", _fail_auth)

    import pytest
    with pytest.raises(litellm.AuthenticationError):
        server.generate_image(model="gemini/gemini-2.5-flash-image", prompt="a cat")

    assert server._provider_errors["gemini"] is not None
    assert "Authentication" in server._provider_errors["gemini"]


def test_research_auth_error_marks_provider_unhealthy(monkeypatch):
    """An auth error during research marks the provider unhealthy."""
    from ask_another.server import ResearchJob

    monkeypatch.setattr(server, "_provider_registry", {"openrouter": "bad-key"})
    monkeypatch.setattr(server, "_provider_errors", {"openrouter": None})

    import litellm

    def _fail_auth(**kwargs):
        raise litellm.AuthenticationError(
            message="Missing Authentication header",
            llm_provider="openrouter",
            model="openrouter/perplexity/sonar-deep-research",
        )

    monkeypatch.setattr(litellm, "completion", _fail_auth)

    job = ResearchJob(
        job_id=99,
        model="openrouter/perplexity/sonar-deep-research",
        query="test",
    )
    server._run_research_completion_sync(job, "bad-key")

    assert job.status == "failed"
    assert server._provider_errors["openrouter"] is not None
    assert "Authentication" in server._provider_errors["openrouter"]


def test_gemini_research_auth_error_marks_provider_unhealthy(monkeypatch):
    """An auth error during Gemini research marks the provider unhealthy."""
    from ask_another.server import ResearchJob

    monkeypatch.setattr(server, "_provider_registry", {"gemini": "bad-key"})
    monkeypatch.setattr(server, "_provider_errors", {"gemini": None})

    import litellm
    import litellm.interactions

    def _fail_auth(**kwargs):
        raise litellm.AuthenticationError(
            message="API key invalid",
            llm_provider="gemini",
            model="gemini/deep-research-pro-preview-12-2025",
        )

    monkeypatch.setattr(litellm.interactions, "create", _fail_auth)

    job = ResearchJob(
        job_id=99,
        model="gemini/deep-research-pro-preview-12-2025",
        query="test",
    )
    server._run_research_gemini_sync(job, "bad-key")

    assert job.status == "failed"
    assert server._provider_errors["gemini"] is not None
    assert "Authentication" in server._provider_errors["gemini"]


def test_completion_auth_error_marks_provider_unhealthy(monkeypatch):
    """An auth error during completion marks the provider unhealthy."""
    monkeypatch.setattr(server, "_provider_registry", {"openrouter": "bad-key"})
    monkeypatch.setattr(server, "_provider_errors", {"openrouter": None})
    monkeypatch.setattr(server, "_model_cache", {
        "openrouter": (["openrouter/deepseek/deepseek-v3.2"], 9999999999.0),
    })
    monkeypatch.setattr(server, "_cache_ttl_minutes", 360)
    monkeypatch.setattr(server, "_zero_data_retention", True)
    monkeypatch.setattr(server, "_annotations", {})
    monkeypatch.setattr(
        server, "_resolve_model",
        lambda m: ("openrouter/deepseek/deepseek-v3.2", "bad-key"),
    )
    monkeypatch.setattr(
        server, "_get_models",
        lambda provider=None, *, zdr=None: ["openrouter/deepseek/deepseek-v3.2"],
    )

    import litellm

    def _fail_auth(**kwargs):
        raise litellm.AuthenticationError(
            message="Missing Authentication header",
            llm_provider="openrouter",
            model="openrouter/deepseek/deepseek-v3.2",
        )

    monkeypatch.setattr(litellm, "completion", _fail_auth)

    import pytest
    with pytest.raises(litellm.AuthenticationError):
        server.completion(model="openrouter/deepseek/deepseek-v3.2", prompt="hi")

    assert server._provider_errors["openrouter"] is not None
    assert "Authentication" in server._provider_errors["openrouter"]
