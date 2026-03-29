# Auth Error Health Marking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a completion/research/image call fails with an authentication error, mark the provider as unhealthy so subsequent searches suppress it and surface the error.

**Architecture:** Catch `litellm.AuthenticationError` in `completion()`, `generate_image()`, `_run_research_completion_sync()`, and `_run_research_gemini_sync()`. On catch, set `_provider_errors[provider] = str(exc)` and re-raise (or set job status to failed for research). The existing filtering from the provider health validation feature handles the rest.

**Tech Stack:** Python, pytest, monkeypatch

---

### Task 1: Mark provider unhealthy on auth error in completion

**Files:**
- Modify: `src/ask_another/server.py:1061-1068` (`completion` function)
- Test: `tests/test_provider_health.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py::test_completion_auth_error_marks_provider_unhealthy -v`
Expected: FAIL — completion currently doesn't catch auth errors

- [ ] **Step 3: Implement auth error handling in completion**

In `src/ask_another/server.py`, wrap the litellm.completion call in `completion()`. Replace lines 1061-1068:

```python
    logger.debug("Calling litellm.completion(model=%s)", full_model)
    try:
        response = litellm.completion(**kwargs)
    except litellm.AuthenticationError as exc:
        _provider_errors[provider] = str(exc)
        logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
        raise
    logger.debug("Completion response received from %s", full_model)

    # Track usage
    _track_usage(full_model)

    return response.choices[0].message.content
```

Note: `provider` is already extracted on line 1031: `provider = full_model.split("/")[0]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ask_another/server.py tests/test_provider_health.py
git commit -m "feat: mark provider unhealthy on auth error in completion"
```

---

### Task 2: Mark provider unhealthy on auth error in generate_image and research

**Files:**
- Modify: `src/ask_another/server.py` (`generate_image` and `_run_research_completion_sync`)
- Test: `tests/test_provider_health.py`

- [ ] **Step 1: Write the failing test for generate_image**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 2: Write the failing test for generate_image (native image model path)**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 3: Write the failing test for research**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py::test_generate_image_auth_error_marks_provider_unhealthy tests/test_provider_health.py::test_generate_image_native_auth_error_marks_provider_unhealthy tests/test_provider_health.py::test_research_auth_error_marks_provider_unhealthy -v`
Expected: 3 FAIL

- [ ] **Step 5: Add auth error handling to generate_image**

In `generate_image()`, add `provider = full_model.split("/")[0]` after `full_model, api_key = _resolve_model(model)` (line 1105).

Then wrap the two litellm call sites. For the completion path (line 1120):

```python
        try:
            response = litellm.completion(**kwargs)
        except litellm.AuthenticationError as exc:
            _provider_errors[provider] = str(exc)
            logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
            raise
```

For the image_generation path (line 1164):

```python
        try:
            response = litellm.image_generation(**kwargs)
        except litellm.AuthenticationError as exc:
            _provider_errors[provider] = str(exc)
            logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
            raise
```

- [ ] **Step 6: Add auth error handling to _run_research_completion_sync**

In `_run_research_completion_sync()`, the existing try/except catches all exceptions. Add a specific `litellm.AuthenticationError` handler before the generic one:

```python
    try:
        response = litellm.completion(**kwargs)
        job.result = response.choices[0].message.content
        job.citations = getattr(response, "citations", []) or []
        job.status = "completed"
        logger.info("Research job %d completed", job.job_id)
    except litellm.AuthenticationError as exc:
        provider = job.model.split("/")[0]
        _provider_errors[provider] = str(exc)
        logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
        job.status = "failed"
        job.error = str(exc)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        logger.warning("Research job %d failed: %s", job.job_id, exc)
    finally:
        job.ended = datetime.now(timezone.utc).strftime("%H:%M")
```

- [ ] **Step 7: Run all tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py -v`
Expected: All PASS

- [ ] **Step 8: Run full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add src/ask_another/server.py tests/test_provider_health.py
git commit -m "feat: mark provider unhealthy on auth error in image gen and research"
```

---

### Task 3: Mark provider unhealthy on auth error in Gemini research

**Files:**
- Modify: `src/ask_another/server.py:1312-1362` (`_run_research_gemini_sync`)
- Test: `tests/test_provider_health.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_provider_health.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py::test_gemini_research_auth_error_marks_provider_unhealthy -v`
Expected: FAIL — current generic `except Exception` doesn't set `_provider_errors`

- [ ] **Step 3: Add auth error handling to _run_research_gemini_sync**

In `_run_research_gemini_sync()`, add a specific `litellm.AuthenticationError` handler before the generic `except Exception` (line 1357):

```python
    except litellm.AuthenticationError as exc:
        provider = job.model.split("/")[0]
        _provider_errors[provider] = str(exc)
        logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
        job.status = "failed"
        job.error = str(exc)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        logger.warning("Gemini research job %d failed: %s", job.job_id, exc)
    finally:
        job.ended = datetime.now(timezone.utc).strftime("%H:%M")
```

Note: `litellm.AuthenticationError` needs to be imported at the top of the function since this file uses lazy imports. The `import litellm` is already present via `import litellm.interactions` on line 1314, so `litellm.AuthenticationError` is accessible.

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_provider_health.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/ask_another/server.py tests/test_provider_health.py
git commit -m "feat: mark provider unhealthy on auth error in Gemini research"
```
