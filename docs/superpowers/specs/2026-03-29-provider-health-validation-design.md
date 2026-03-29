# Provider Health Validation

**Date:** 2026-03-29
**Status:** Draft
**Addresses feedback:** #2 — unconfigured/broken providers surface models that can't be called

## Problem

When a provider is configured via `PROVIDER_*` env vars but its API key is invalid (or the provider API is down), model discovery still attempts to list models. The fetch fails silently — models return empty, but the provider stays in the registry. This means:

- Unhealthy providers are retried on every `_get_models()` call until cache TTL expires
- If models from that provider exist in annotations (e.g., favourites from prior sessions), they appear in instructions, favourites, top rated, and recently added — even though they can't be called
- The user gets no indication that a provider is broken

## Design

### Core State

```python
_provider_errors: dict[str, str | None] = {}
```

- Key: provider name (e.g., `"gemini"`)
- Value: `None` = healthy, `str` = actual error message from the provider

### When Validation Runs

1. **Startup** — during `_refresh_provider_models()`. Each provider's fetch result sets its health status in `_provider_errors`.
2. **Targeted search** — when `search_models` or `search_families` is called with a `search` term that matches an unhealthy provider name, re-attempt that provider's fetch before returning results. If it succeeds, clear the error and include the models. If it still fails, update the error and append it to the results.
3. **`refresh_models`** — already re-scans all providers, so health is re-evaluated naturally.

### How Validation Works

Uses the existing `_fetch_models()` call — no separate ping endpoint.

- If `_fetch_models()` returns a non-empty list: `_provider_errors[provider] = None`
- If `_fetch_models()` raises an exception: `_provider_errors[provider] = str(exc)`
- If `_fetch_models()` returns an empty list without exception: `_provider_errors[provider] = "No models returned"`

### Filtering

`_get_models()` skips providers where `_provider_errors.get(provider)` is not `None`. This single filter point automatically suppresses unhealthy providers from:

- `search_models` results
- `search_families` results
- Favourites in `_build_instructions()`
- Top rated in `_build_instructions()`
- Recently added in `_build_instructions()`

### Surfacing

**In `_build_instructions()`:** Add an "Unavailable Providers" section listing each unhealthy provider with its error message. Example:

```
Unavailable Providers:
  - gemini: Google API key is required. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
```

**In search results:** When a targeted search matches an unhealthy provider and the retry still fails, append the error to the response. Example:

```
⚠️ gemini is configured but unavailable: Google API key is required. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.
```

### Targeted Search Retry Logic

In `search_models` and `search_families`, before filtering results:

1. Check if the `search` term matches any provider name in `_provider_errors` that has a non-`None` value
2. If so, re-attempt `_fetch_models()` for that provider
3. If the retry succeeds, clear `_provider_errors[provider]`, add models to cache, include in results
4. If the retry fails, update `_provider_errors[provider]` with the new error, append warning to results

Match logic: `search.lower()` is a substring of the provider name, or the provider name is a substring of `search.lower()`.

## Scope

### In scope
- `_provider_errors` dict and population in `_refresh_provider_models()`
- Filtering in `_get_models()`
- Surfacing in `_build_instructions()`
- Retry + error surfacing in `search_models` and `search_families`
- Retry in `refresh_models` (already covered — it calls `_refresh_provider_models()`)

### Out of scope
- Validating keys without attempting a model fetch (no lightweight ping)
- Periodic background re-validation (only on-demand)
- Per-model health checks (this is provider-level only)

## Testing

- Test that a provider with a bad key is marked unhealthy at startup
- Test that unhealthy providers are excluded from `_get_models()` results
- Test that `_build_instructions()` includes the unavailable providers section
- Test that a targeted search for an unhealthy provider triggers a retry
- Test that a successful retry clears the error and includes models
- Test that `refresh_models` re-evaluates health for all providers
