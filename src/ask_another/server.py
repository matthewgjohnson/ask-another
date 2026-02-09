"""MCP server implementation for ask-another v2."""

import json
import os
import re
import time
import urllib.request
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ask-another")

# Provider registry: {provider_name: api_key}
_provider_registry: dict[str, str] = {}

# Favourites: list of full model identifiers
_favourites: list[str] = []

# Cache: {provider_name: (model_ids, timestamp)}
_model_cache: dict[str, tuple[list[str], float]] = {}

# Cache TTL in seconds (default 6 hours)
_cache_ttl: int = 21600


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _parse_provider_config(var_name: str, value: str) -> tuple[str, str]:
    """Parse a PROVIDER_* environment variable.

    Expected format: provider-name;api-key
    """
    if ";" not in value:
        raise ValueError(
            f"Invalid format for {var_name}: expected 'provider-name;api-key'"
        )

    parts = value.split(";", 1)
    provider = parts[0].strip()
    api_key = parts[1].strip()

    if not provider:
        raise ValueError(f"Invalid format for {var_name}: provider name is empty")
    if not api_key:
        raise ValueError(f"Invalid format for {var_name}: API key is empty")

    return provider, api_key


def _parse_favourites(value: str) -> list[str]:
    """Parse the FAVOURITES environment variable.

    Validates one favourite per provider prefix.
    """
    if not value.strip():
        return []

    favourites = [f.strip() for f in value.split(",") if f.strip()]

    seen_prefixes: dict[str, str] = {}
    for fav in favourites:
        prefix = fav.split("/")[0]
        if prefix in seen_prefixes:
            raise ValueError(
                f"Multiple favourites for provider '{prefix}': "
                f"'{seen_prefixes[prefix]}' and '{fav}'"
            )
        seen_prefixes[prefix] = fav

    return favourites


def _load_config() -> None:
    """Scan environment and populate provider registry, favourites, and cache TTL."""
    global _provider_registry, _favourites, _cache_ttl

    _provider_registry = {}
    provider_pattern = re.compile(r"^PROVIDER_\w+$")

    for var_name, value in os.environ.items():
        if provider_pattern.match(var_name):
            provider, api_key = _parse_provider_config(var_name, value)
            _provider_registry[provider] = api_key

    favourites_str = os.environ.get("FAVOURITES", "")
    _favourites = _parse_favourites(favourites_str)

    ttl_str = os.environ.get("CACHE_TTL", "360")
    try:
        _cache_ttl = int(ttl_str) * 60
    except ValueError:
        raise ValueError(f"Invalid CACHE_TTL value: {ttl_str}")


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------


def _normalise_model_id(model_id: str, provider: str) -> str:
    """Ensure a model ID has the provider prefix."""
    if not model_id.startswith(f"{provider}/"):
        return f"{provider}/{model_id}"
    return model_id


def _fetch_openrouter_models(api_key: str) -> list[str]:
    """Fetch models from OpenRouter's API directly."""
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return [f"openrouter/{m['id']}" for m in data.get("data", [])]


# Providers where LiteLLM listing does not work
_LISTING_EXCEPTIONS: dict[str, Callable[[str], list[str]]] = {
    "openrouter": _fetch_openrouter_models,
}


def _fetch_models(provider: str, api_key: str) -> list[str]:
    """Fetch the model list for a provider."""
    if provider in _LISTING_EXCEPTIONS:
        return _LISTING_EXCEPTIONS[provider](api_key)

    import litellm

    try:
        models = litellm.get_valid_models(
            check_provider_endpoint=True,
            custom_llm_provider=provider,
            api_key=api_key,
        )
    except Exception:
        return []

    return [_normalise_model_id(m, provider) for m in models]


def _get_models(provider: str | None = None) -> list[str]:
    """Get models, serving from cache when possible."""
    now = time.time()
    providers = [provider] if provider else list(_provider_registry.keys())
    all_models: list[str] = []

    for p in providers:
        if p not in _provider_registry:
            continue

        if p in _model_cache:
            cached_models, cached_at = _model_cache[p]
            if now - cached_at < _cache_ttl:
                all_models.extend(cached_models)
                continue

        try:
            models = _fetch_models(p, _provider_registry[p])
            _model_cache[p] = (models, now)
            all_models.extend(models)
        except Exception:
            pass

    return sorted(all_models)


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------


def _resolve_model(model: str) -> tuple[str, str]:
    """Resolve a model identifier or shorthand to (full_id, api_key)."""
    if "/" in model:
        for provider, api_key in _provider_registry.items():
            if model.startswith(f"{provider}/"):
                return model, api_key
        raise ValueError("Model not found. Use list_models to see available models")

    # Shorthand: match against favourites by provider prefix
    for fav in _favourites:
        if fav.startswith(f"{model}/"):
            for provider, api_key in _provider_registry.items():
                if fav.startswith(f"{provider}/"):
                    return fav, api_key

    fav_list = ", ".join(_favourites) if _favourites else "(none configured)"
    raise ValueError(
        f"No favourite matches '{model}'. Available favourites: {fav_list}"
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

_load_config()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_models(
    provider: str | None = None,
    favourites_only: bool = False,
) -> list[str]:
    """List available model identifiers.

    Args:
        provider: Filter results to a single provider (e.g. 'openai', 'openrouter')
        favourites_only: Return only favourite models. Defaults to false.

    Returns:
        Array of model identifiers in 'provider/model-name' format.
    """
    if favourites_only:
        results = list(_favourites)
        if provider:
            results = [f for f in results if f.startswith(f"{provider}/")]
        return results

    return _get_models(provider=provider)


@mcp.tool()
def completion(
    model: str,
    prompt: str,
    system: str | None = None,
    temperature: float = 1.0,
) -> str:
    """Get a completion from the specified LLM.

    Args:
        model: Full model identifier (e.g. 'openai/gpt-4o') or favourite shorthand (e.g. 'openai')
        prompt: The user prompt to send to the model
        system: Optional system prompt
        temperature: Sampling temperature (0.0-2.0, default 1.0)

    Returns:
        The model's text response
    """
    import litellm

    full_model, api_key = _resolve_model(model)

    if not 0.0 <= temperature <= 2.0:
        raise ValueError("Temperature must be between 0.0 and 2.0")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = litellm.completion(
        model=full_model,
        messages=messages,
        temperature=temperature,
        api_key=api_key,
        timeout=60,
    )

    return response.choices[0].message.content


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
