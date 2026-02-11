"""MCP server implementation for ask-another v2."""

import json
import os
import re
import time
import urllib.request
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

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


def _get_family(model_id: str) -> str:
    """Extract family from a model identifier (all path segments except the last)."""
    return model_id.rsplit("/", 1)[0]


def _parse_favourites(value: str) -> list[str]:
    """Parse the FAVOURITES environment variable.

    Validates one favourite per family.
    """
    if not value.strip():
        return []

    favourites = [f.strip() for f in value.split(",") if f.strip()]

    seen_families: dict[str, str] = {}
    for fav in favourites:
        family = _get_family(fav)
        if family in seen_families:
            raise ValueError(
                f"Multiple favourites for family '{family}': "
                f"'{seen_families[family]}' and '{fav}'"
            )
        seen_families[family] = fav

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
            if models:
                _model_cache[p] = (models, now)
                all_models.extend(models)
        except Exception:
            pass

    return sorted(all_models)


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------


def _resolve_model(model: str) -> tuple[str, str]:
    """Resolve a model identifier or shorthand to (full_id, api_key).

    Resolution order:
    1. Shorthand: if any favourite starts with model/, resolve via favourites
    2. Full identifier: route directly by matching provider prefix
    """
    # Try shorthand resolution against favourites first
    matches = [fav for fav in _favourites if fav.startswith(f"{model}/")]

    if len(matches) == 1:
        fav = matches[0]
        for provider, api_key in _provider_registry.items():
            if fav.startswith(f"{provider}/"):
                return fav, api_key

    if len(matches) > 1:
        match_list = ", ".join(matches)
        raise ValueError(
            f"Ambiguous shorthand '{model}' matches multiple favourites: {match_list}. "
            f"Use a more specific shorthand (e.g. '{_get_family(matches[0])}')"
        )

    # Full identifier: route directly
    if "/" in model:
        for provider, api_key in _provider_registry.items():
            if model.startswith(f"{provider}/"):
                return model, api_key

    fav_list = ", ".join(_favourites) if _favourites else "(none configured)"
    raise ValueError(
        f"No favourite matches '{model}'. Available favourites: {fav_list}"
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

_load_config()


def _build_instructions() -> str:
    """Build server instructions dynamically from config."""
    lines = [
        "Purpose:",
        "  - Ask another LLM for a second opinion.",
        "  - Provide access to other models through litellm.",
        "Howto:",
        "  - For a quick query, use completion with a favourite model (see below).",
        "  - To use another model: search_families → search_models → completion.",
        "  - Never guess model IDs.",
    ]
    if _favourites:
        lines.append("Favourite Models:")
        for fav in _favourites:
            lines.append(f"  - {fav}")
    return "\n".join(lines)


mcp = FastMCP("ask-another", instructions=_build_instructions())


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_families(
    search: str | None = None,
    favourites_only: bool = False,
) -> str:
    """Browse available provider groupings (e.g. 'openai', 'openrouter/deepseek').
    Use this to explore what's available before drilling into specific models
    with search_models.

    Args:
        search: Substring filter applied to family names
        favourites_only: Return only families containing favourite models
    """
    if favourites_only:
        families = sorted(set(_get_family(f) for f in _favourites))
    else:
        all_models = _get_models()
        families = sorted(set(_get_family(m) for m in all_models))

    if search:
        families = [f for f in families if search.lower() in f.lower()]

    return "\n".join(families)


@mcp.tool()
def search_models(
    search: str | None = None,
    favourites_only: bool = False,
) -> str:
    """Find exact model identifiers. Always call this to verify a model ID
    before passing it to completion — do not guess IDs.

    Args:
        search: Substring filter applied to full model identifiers
        favourites_only: Return only favourite models
    """
    if favourites_only:
        models = list(_favourites)
    else:
        models = _get_models()

    if search:
        models = [m for m in models if search.lower() in m.lower()]

    return "\n".join(models)


@mcp.tool()
def completion(
    model: str,
    prompt: str,
    system: str | None = None,
    temperature: float | None = None,
) -> str:
    """Call a model. Use a favourite shorthand (e.g. 'openai') or an exact
    model ID verified via search_models. Do not set temperature unless you
    have a specific reason — some models reject non-default values.

    Args:
        model: Full model identifier (e.g. 'openai/gpt-4o') or favourite shorthand (e.g. 'openai').
               Use search_models to find valid identifiers.
        prompt: The user prompt to send to the model
        system: Optional system prompt
        temperature: Sampling temperature (0.0-2.0). Omit to use model default.
    """
    import litellm

    full_model, api_key = _resolve_model(model)

    if temperature is not None and not 0.0 <= temperature <= 2.0:
        raise ValueError("Temperature must be between 0.0 and 2.0")

    # Validate model exists in discovered models
    provider = full_model.split("/")[0]
    known_models = _get_models(provider)
    if known_models and full_model not in known_models:
        model_name = full_model.split("/", 1)[1] if "/" in full_model else full_model
        suggestions = [
            m for m in known_models
            if model_name.split("-")[0] in m.lower()
        ][:5]
        msg = f"Model '{full_model}' not found in {provider}'s model list."
        if suggestions:
            msg += f" Similar models: {', '.join(suggestions)}"
        msg += " Use search_models to find valid identifiers."
        raise ValueError(msg)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict = {
        "model": full_model,
        "messages": messages,
        "api_key": api_key,
        "timeout": 60,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    response = litellm.completion(**kwargs)

    return response.choices[0].message.content


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
