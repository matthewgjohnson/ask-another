# Provider Health Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate provider API keys at startup, suppress broken providers from all results, and surface actual error messages to the user.

**Architecture:** Add a `_provider_errors: dict[str, str | None]` module-level dict alongside `_provider_registry`. Populated during `_refresh_provider_models()`, checked in `_get_models()` and `_build_instructions()`. Unhealthy providers are retried when explicitly searched for or when `refresh_models` is called.

**Tech Stack:** Python, pytest, monkeypatch

---

### Task 1: Add `_provider_errors` state and populate during refresh

**Files:**
- Modify: `src/ask_another/server.py:126-142` (module-level state)
- Modify: `src/ask_another/server.py:432-457` (`_refresh_provider_models` and `_startup_enrich`)
- Test: `tests/test_provider_health.py`

- [ ] **Step 1: Write the failing test — healthy provider**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py::test_healthy_provider_has_no_error -v`
Expected: FAIL — `_provider_errors` attribute does not exist yet

- [ ] **Step 3: Write the failing test — unhealthy provider**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 4: Write the failing test — empty model list**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 5: Add `_provider_errors` to module-level state**

In `src/ask_another/server.py`, after line 136 (`_zero_data_retention`), add:

```python
# Provider health: None = healthy, str = error message
_provider_errors: dict[str, str | None] = {}
```

- [ ] **Step 6: Update `_refresh_provider_models` to populate `_provider_errors`**

Replace the body of `_refresh_provider_models()` in `src/ask_another/server.py`:

```python
def _refresh_provider_models() -> None:
    """Scan all configured providers and populate the model cache."""
    for provider, api_key in _provider_registry.items():
        effective_zdr = _zero_data_retention
        cache_key = f"{provider}:zdr={effective_zdr}" if provider == "openrouter" else provider
        try:
            if provider == "openrouter":
                models, or_metadata = _fetch_openrouter_models(api_key, zdr=effective_zdr)
                # Merge OpenRouter metadata into annotations
                for model_id, meta in or_metadata.items():
                    entry = _annotations.setdefault(model_id, {})
                    entry.setdefault("metadata", {}).update(meta)
            else:
                models = _fetch_models(provider, api_key, zdr=effective_zdr)
            if models:
                _model_cache[cache_key] = (models, time.time())
                _provider_errors[provider] = None
                logger.info("Cached %d models for %s", len(models), provider)
            else:
                _provider_errors[provider] = "No models returned"
                logger.warning("Provider %s returned no models", provider)
        except Exception as exc:
            _provider_errors[provider] = str(exc)
            logger.warning("Failed to refresh models for %s: %s", provider, exc)
```

- [ ] **Step 7: Add `_provider_errors` to `_load_config` global declaration**

In `_load_config()`, update the global declaration line:

```python
global _provider_registry, _cache_ttl_minutes, _zero_data_retention, _annotations, _provider_errors
```

And add after `_provider_registry = {}`:

```python
_provider_errors = {}
```

- [ ] **Step 8: Run all three tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py -v`
Expected: 3 PASS

- [ ] **Step 9: Commit**

```bash
git add tests/test_provider_health.py src/ask_another/server.py
git commit -m "feat: add _provider_errors state and populate during refresh"
```

---

### Task 2: Filter unhealthy providers in `_get_models`

**Files:**
- Modify: `src/ask_another/server.py:396-429` (`_get_models`)
- Test: `tests/test_provider_health.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py::test_get_models_skips_unhealthy_providers -v`
Expected: FAIL — gemini models would be fetched (or attempted)

- [ ] **Step 3: Add filter to `_get_models`**

In `_get_models()`, at the start of the `for p in providers:` loop body, add a skip check:

```python
        if _provider_errors.get(p):
            continue
```

This goes right after `if p not in _provider_registry: continue` (the existing check).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ask_another/server.py tests/test_provider_health.py
git commit -m "feat: filter unhealthy providers from _get_models"
```

---

### Task 3: Filter unhealthy providers in `_build_instructions`

**Files:**
- Modify: `src/ask_another/server.py:681-760` (`_build_instructions`)
- Test: `tests/test_provider_health.py`

- [ ] **Step 1: Write the failing test — favourites filtered**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 2: Write the failing test — unavailable providers section**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py::test_build_instructions_excludes_unhealthy_favourites tests/test_provider_health.py::test_build_instructions_shows_unavailable_providers -v`
Expected: 2 FAIL

- [ ] **Step 4: Add helper to get unhealthy provider set**

In `src/ask_another/server.py`, add a module-level helper (near `_get_favourites`):

```python
def _unhealthy_providers() -> set[str]:
    """Return the set of provider names that have errors."""
    return {p for p, err in _provider_errors.items() if err}
```

- [ ] **Step 5: Filter favourites, top rated, and recently added in `_build_instructions`**

In `_build_instructions()`, add filtering after deriving each list. The filter checks whether the model's provider prefix is in the unhealthy set.

After `favourites = _get_favourites(_annotations)`:

```python
    unhealthy = _unhealthy_providers()
    favourites = [f for f in favourites if f.split("/")[0] not in unhealthy]
```

For the `rated` list comprehension, add the same filter:

```python
    rated = [
        (model_id, entry.get("metadata", {}).get("arena_elo", 0))
        for model_id, entry in _annotations.items()
        if entry.get("metadata", {}).get("arena_elo")
        and model_id.split("/")[0] not in unhealthy
    ]
```

For the `recent` call, filter after:

```python
    recent = _get_recent_models(_annotations, days=7)
    recent = [(m, d) for m, d in recent if m.split("/")[0] not in unhealthy]
```

- [ ] **Step 6: Add "Unavailable Providers" section to `_build_instructions`**

At the end of `_build_instructions()`, before `return "\n".join(lines)`:

```python
    errors = {p: err for p, err in _provider_errors.items() if err}
    if errors:
        lines.append("Unavailable Providers:")
        for provider, err in sorted(errors.items()):
            lines.append(f"  - {provider}: {err}")
```

- [ ] **Step 7: Run all tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py -v`
Expected: 6 PASS

- [ ] **Step 8: Run existing annotation tests to check for regressions**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add src/ask_another/server.py tests/test_provider_health.py
git commit -m "feat: filter unhealthy providers from instructions and show errors"
```

---

### Task 4: Targeted search retry for unhealthy providers

**Files:**
- Modify: `src/ask_another/server.py:783-847` (`search_families` and `search_models`)
- Test: `tests/test_provider_health.py`

- [ ] **Step 1: Write the failing test — retry succeeds**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 2: Write the failing test — retry still fails**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py::test_search_models_retries_unhealthy_provider tests/test_provider_health.py::test_search_models_shows_error_on_retry_failure -v`
Expected: 2 FAIL

- [ ] **Step 4: Add retry helper function**

In `src/ask_another/server.py`, add a helper near the other model discovery functions:

```python
def _retry_unhealthy_providers(search: str, *, zdr: bool | None = None) -> str | None:
    """Re-attempt fetch for unhealthy providers matching a search term.

    Returns a warning string if any provider was retried and still failed,
    or None if all retries succeeded (or no retries were needed).
    """
    effective_zdr = zdr if zdr is not None else _zero_data_retention
    warnings = []
    for provider, err in list(_provider_errors.items()):
        if not err:
            continue
        if search.lower() not in provider.lower() and provider.lower() not in search.lower():
            continue
        # Retry
        cache_key = f"{provider}:zdr={effective_zdr}" if provider == "openrouter" else provider
        try:
            if provider == "openrouter":
                models, or_metadata = _fetch_openrouter_models(
                    _provider_registry[provider], zdr=effective_zdr
                )
                for model_id, meta in or_metadata.items():
                    entry = _annotations.setdefault(model_id, {})
                    entry.setdefault("metadata", {}).update(meta)
            else:
                models = _fetch_models(provider, _provider_registry[provider], zdr=effective_zdr)
            if models:
                _model_cache[cache_key] = (models, time.time())
                _provider_errors[provider] = None
                logger.info("Retry succeeded for %s: %d models", provider, len(models))
            else:
                _provider_errors[provider] = "No models returned"
                warnings.append(f"⚠️ {provider} is configured but unavailable: No models returned")
        except Exception as exc:
            _provider_errors[provider] = str(exc)
            warnings.append(f"⚠️ {provider} is configured but unavailable: {exc}")
            logger.warning("Retry failed for %s: %s", provider, exc)
    return "\n".join(warnings) if warnings else None
```

- [ ] **Step 5: Call retry helper in `search_models`**

In `search_models()`, add retry logic before the existing `models = _get_models(zdr=zdr)` call:

```python
    retry_warning = None
    if search:
        retry_warning = _retry_unhealthy_providers(search, zdr=zdr)

    models = _get_models(zdr=zdr)
```

And at the end, before `return`, append the warning:

```python
    result = _zdr_warning(zdr, result)
    if retry_warning:
        result = f"{result}\n\n{retry_warning}" if result else retry_warning
    return result
```

- [ ] **Step 6: Call retry helper in `search_families`**

Same pattern in `search_families()`:

```python
    retry_warning = None
    if search:
        retry_warning = _retry_unhealthy_providers(search, zdr=zdr)

    all_models = _get_models(zdr=zdr)
```

And at the end:

```python
    result = _zdr_warning(zdr, result)
    if retry_warning:
        result = f"{result}\n\n{retry_warning}" if result else retry_warning
    return result
```

- [ ] **Step 7: Run all tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py -v`
Expected: 8 PASS

- [ ] **Step 8: Run full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add src/ask_another/server.py tests/test_provider_health.py
git commit -m "feat: retry unhealthy providers on targeted search"
```

---

### Task 5: Integration smoke test and cleanup

**Files:**
- Test: `tests/test_provider_health.py`

- [ ] **Step 1: Write integration test — full flow**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py::test_full_flow_healthy_and_unhealthy -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_provider_health.py
git commit -m "test: add integration test for provider health validation"
```
