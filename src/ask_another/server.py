"""MCP server implementation for ask-another v2."""

from __future__ import annotations

import asyncio
import base64
import csv
import io
import logging
import logging.handlers
import json
import os
import re
import time
import urllib.request
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections.abc import AsyncIterator
from typing import Any, cast

logger = logging.getLogger(__name__)

import anyio
import anyio.abc
import anyio.to_thread
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

# In-memory annotations: {model_id: {metadata: {...}, usage: {...}, annotations: {...}}}
_annotations: dict[str, dict] = {}


def _get_annotations_path() -> Path:
    """Return the annotations file path from env or default."""
    return Path(
        os.environ.get("ANNOTATIONS_FILE", os.path.expanduser("~/.ask-another-annotations.json"))
    )


def _load_annotations() -> dict[str, dict]:
    """Load annotations from the JSON file. Returns empty dict if missing."""
    path = _get_annotations_path()
    if not path.is_file():
        logger.debug("No annotations file at %s", path)
        return {}
    try:
        data = json.loads(path.read_text())
        logger.debug("Loaded %d annotations from %s", len(data), path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load annotations from %s: %s", path, exc)
        return {}


def _save_annotations(data: dict[str, dict]) -> None:
    """Save annotations to the JSON file (atomic write via temp + rename)."""
    path = _get_annotations_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)
    logger.debug("Saved %d annotations to %s", len(data), path)


def _track_usage(model_id: str) -> None:
    """Increment call_count and update last_used for a model."""
    entry = _annotations.setdefault(model_id, {})
    usage = entry.setdefault("usage", {"call_count": 0, "last_used": ""})
    usage["call_count"] = usage.get("call_count", 0) + 1
    usage["last_used"] = datetime.now(timezone.utc).isoformat()
    _save_annotations(_annotations)


def _get_favourites(annotations: dict[str, dict]) -> list[str]:
    """Derive top 5 favourite models by call_count from annotations."""
    models_with_usage = [
        (model_id, entry.get("usage", {}).get("call_count", 0))
        for model_id, entry in annotations.items()
        if entry.get("usage", {}).get("call_count", 0) > 0
    ]
    models_with_usage.sort(key=lambda x: x[1], reverse=True)
    return [model_id for model_id, _ in models_with_usage[:5]]


def _needs_refresh(annotations: dict[str, dict]) -> bool:
    """Check if enriched model metadata is stale or missing.

    Only considers entries that have a 'metadata' sub-object (i.e. have been
    through enrichment before). Usage-only entries are ignored — they'll get
    metadata on the next enrichment cycle.
    """
    if not annotations:
        return True
    enriched = [e for e in annotations.values() if "metadata" in e]
    if not enriched:
        return True
    now = datetime.now(timezone.utc)
    for entry in enriched:
        last = entry["metadata"].get("last_updated")
        if not last:
            return True
        try:
            updated_at = datetime.fromisoformat(last)
            if (now - updated_at).total_seconds() > _cache_ttl_minutes * 60:
                return True
        except (ValueError, TypeError):
            return True
    return False


def _unhealthy_providers() -> set[str]:
    """Return the set of provider names that have errors."""
    return {p for p, err in _provider_errors.items() if err}


def _get_recent_models(annotations: dict[str, dict], days: int = 7) -> list[tuple[str, str]]:
    """Return models first seen within the last N days, newest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for model_id, entry in annotations.items():
        first_seen = entry.get("metadata", {}).get("first_seen")
        if not first_seen:
            continue
        try:
            seen_dt = datetime.fromisoformat(first_seen)
            if seen_dt >= cutoff:
                recent.append((model_id, first_seen[:10]))  # date only
        except (ValueError, TypeError):
            continue
    recent.sort(key=lambda x: x[1], reverse=True)
    return recent


# Provider registry: {provider_name: api_key}
_provider_registry: dict[str, str] = {}

# Cache: {provider_name: (model_ids, timestamp)}
_model_cache: dict[str, tuple[list[str], float]] = {}

# Cache TTL in seconds (default 6 hours)
_cache_ttl_minutes: int = 360

# Whether to filter OpenRouter models to ZDR-compatible only (default: on)
_zero_data_retention: bool = True

# Provider health: None = healthy, str = error message
_provider_errors: dict[str, str | None] = {}

# Providers that failed with auth errors at runtime (not retryable via discovery)
_provider_auth_errors: set[str] = set()

# Feedback log path
_feedback_log: Path = Path(
    os.environ.get("FEEDBACK_LOG", os.path.expanduser("~/.ask-another-feedback.jsonl"))
)


# ---------------------------------------------------------------------------
# Research job store
# ---------------------------------------------------------------------------


@dataclass
class ResearchJob:
    """Tracks a background research task."""

    job_id: int
    model: str
    query: str
    status: str = "in_progress"  # in_progress | completed | failed | cancelled
    started: str = ""
    ended: str = ""
    result: str | None = None
    citations: list[str] = field(default_factory=list)
    error: str = ""
    _task_scope: anyio.CancelScope | None = field(default=None, repr=False)


class JobStore:
    """In-memory store for research jobs, shared via lifespan context."""

    def __init__(self, task_group: anyio.abc.TaskGroup) -> None:
        self.task_group = task_group
        self._jobs: dict[int, ResearchJob] = {}
        self._next_id: int = 1

    def create_job(self, model: str, query: str) -> ResearchJob:
        job = ResearchJob(
            job_id=self._next_id,
            model=model,
            query=query,
            started=datetime.now(timezone.utc).strftime("%H:%M"),
        )
        self._jobs[job.job_id] = job
        self._next_id += 1
        return job

    def get_job(self, job_id: int) -> ResearchJob | None:
        return self._jobs.get(job_id)

    def all_jobs(self) -> list[ResearchJob]:
        return list(self._jobs.values())


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Lifespan context: populate caches and enrich on startup."""
    async with anyio.create_task_group() as tg:
        # Startup enrichment (run in thread to not block)
        if _needs_refresh(_annotations):
            await anyio.to_thread.run_sync(_startup_enrich)
        yield {"job_store": JobStore(tg)}


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



def _configure_logging() -> None:
    """Set up file-based debug logging if LOG_LEVEL is set.

    Env vars:
        LOG_LEVEL: DEBUG, INFO, WARNING, ERROR. Empty = disabled.
        LOG_FILE: Path to log file (default: ~/.ask-another.log).
        LOG_FILE_SIZE: Max file size in MB (default: 5).
        LOG_FILE_COUNT: Number of backup files (default: 2).
    """
    level_str = os.environ.get("LOG_LEVEL", "").strip().upper()
    if not level_str:
        return

    level = getattr(logging, level_str, None)
    if level is None:
        return

    log_file = os.path.expanduser(
        os.environ.get("LOG_FILE", "~/.ask-another.log")
    )
    try:
        max_bytes = int(os.environ.get("LOG_FILE_SIZE", "5")) * 1024 * 1024
    except ValueError:
        max_bytes = 5 * 1024 * 1024
    try:
        backup_count = int(os.environ.get("LOG_FILE_COUNT", "2"))
    except ValueError:
        backup_count = 2

    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.info("ask-another logging started (level=%s, file=%s)", level_str, log_file)


def _load_config() -> None:
    """Scan environment and populate provider registry and cache TTL."""
    global _provider_registry, _cache_ttl_minutes, _zero_data_retention, _annotations, _provider_errors, _provider_auth_errors

    _configure_logging()

    _provider_registry = {}
    _provider_errors = {}
    _provider_auth_errors = set()
    provider_pattern = re.compile(r"^PROVIDER_\w+$")

    for var_name, value in os.environ.items():
        if provider_pattern.match(var_name):
            provider, api_key = _parse_provider_config(var_name, value)
            _provider_registry[provider] = api_key

    ttl_str = os.environ.get("CACHE_TTL_MINUTES", "360")
    try:
        _cache_ttl_minutes = int(ttl_str)
    except ValueError:
        raise ValueError(f"Invalid CACHE_TTL_MINUTES value: {ttl_str}")

    zdr_val = os.environ.get("ZERO_DATA_RETENTION", "").lower()
    if zdr_val:
        _zero_data_retention = zdr_val in ("1", "true", "yes")
    else:
        _zero_data_retention = True

    _annotations = _load_annotations()

    logger.info(
        "Config loaded: %d providers, %d annotations, ZDR=%s, cache_ttl=%dm",
        len(_provider_registry), len(_annotations),
        _zero_data_retention, _cache_ttl_minutes,
    )


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------


def _normalise_model_id(model_id: str, provider: str) -> str:
    """Ensure a model ID has the provider prefix."""
    if not model_id.startswith(f"{provider}/"):
        return f"{provider}/{model_id}"
    return model_id


def _fetch_openrouter_models(
    api_key: str, *, zdr: bool = False
) -> tuple[list[str], dict[str, dict]]:
    """Fetch models from OpenRouter's API directly.

    Returns (model_ids, metadata_dict). Metadata (pricing, context length,
    listing date) always comes from the public /api/v1/models endpoint.
    When zdr is True, the model list comes from the ZDR endpoint but
    metadata is filtered to only ZDR-compatible models.
    """
    # Always fetch metadata from the public models endpoint
    pub_req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(pub_req, timeout=60) as resp:
        pub_data = json.loads(resp.read())

    all_metadata: dict[str, dict] = {}
    for m in pub_data.get("data", []):
        model_id = f"openrouter/{m['id']}"
        pricing = m.get("pricing") or {}
        all_metadata[model_id] = {
            "context_length": m.get("context_length"),
            "pricing_in": pricing.get("prompt"),
            "pricing_out": pricing.get("completion"),
            "openrouter_listed": m.get("created"),
        }

    if zdr:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/endpoints/zdr",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        seen: set[str] = set()
        models: list[str] = []
        for endpoint in data.get("data", []):
            model_id = endpoint.get("model_id", "")
            if model_id and model_id not in seen:
                seen.add(model_id)
                models.append(f"openrouter/{model_id}")
        logger.debug("OpenRouter ZDR endpoint returned %d models", len(models))
        # Return metadata only for ZDR-compatible models
        zdr_metadata = {k: v for k, v in all_metadata.items() if k in models}
        return models, zdr_metadata

    models = list(all_metadata.keys())
    logger.debug("OpenRouter models endpoint returned %d models", len(models))
    return models, all_metadata


def _fetch_models(provider: str, api_key: str, *, zdr: bool = False) -> list[str]:
    """Fetch the model list for a provider."""
    if provider == "openrouter":
        models, _ = _fetch_openrouter_models(api_key, zdr=zdr)
        return models

    import litellm

    try:
        models = litellm.get_valid_models(
            check_provider_endpoint=True,
            custom_llm_provider=provider,
            api_key=api_key,
        )
    except Exception as exc:
        logger.warning("Failed to fetch models for %s: %s", provider, exc)
        return []

    return [_normalise_model_id(m, provider) for m in models]


def _get_models(provider: str | None = None, *, zdr: bool | None = None) -> list[str]:
    """Get models, serving from cache when possible.

    Args:
        provider: Limit to a single provider. None = all providers.
        zdr: Override ZDR filtering for OpenRouter. None = use global default.
    """
    effective_zdr = zdr if zdr is not None else _zero_data_retention
    now = time.time()
    providers = [provider] if provider else list(_provider_registry.keys())
    all_models: list[str] = []

    for p in providers:
        if p not in _provider_registry:
            continue

        if _provider_errors.get(p):
            continue

        cache_key = f"{p}:zdr={effective_zdr}" if p == "openrouter" else p

        if cache_key in _model_cache:
            cached_models, cached_at = _model_cache[cache_key]
            if now - cached_at < _cache_ttl_minutes * 60:
                logger.debug("Cache hit for %s (%d models)", cache_key, len(cached_models))
                all_models.extend(cached_models)
                continue

        try:
            models = _fetch_models(p, _provider_registry[p], zdr=effective_zdr)
            if models:
                _model_cache[cache_key] = (models, now)
                all_models.extend(models)
        except Exception as exc:
            logger.warning("Model fetch failed for provider %s: %s", p, exc)

    return sorted(all_models)


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
        if provider in _provider_auth_errors:
            warnings.append(f"⚠️ {provider} is configured but unavailable: {err}")
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


def _startup_enrich() -> None:
    """Refresh provider models and fetch benchmark data."""
    _refresh_provider_models()
    _fetch_enrichment()
    logger.info("Startup enrichment complete")


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

# Regex for date suffixes: -YYYYMMDD or -YY-MM-DD
_DATE_SUFFIX_RE = re.compile(r"-\d{4}-?\d{2}-?\d{2}$")
# Suffixes to strip (order matters: dates first, then these)
_STRIP_SUFFIXES = ("-preview", "-latest", "-experimental", "-exp")


def _normalize_model_name(name: str) -> str:
    """Normalize a model name for matching arena keys to provider IDs.

    Strips provider prefix, date suffixes, and common suffixes like -preview.
    Does NOT strip version suffixes like -v3 or -v3.2.
    """
    # Lowercase
    name = name.lower()
    # Strip provider prefix (everything up to last /)
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    # Strip date suffixes first
    name = _DATE_SUFFIX_RE.sub("", name)
    # Strip known suffixes
    for suffix in _STRIP_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break  # Only strip one suffix
    return name


_ARENA_CATALOG_URL = (
    "https://raw.githubusercontent.com/lmarena/arena-catalog/main/data/leaderboard-text.json"
)
_ARENA_METADATA_BASE = (
    "https://huggingface.co/spaces/lmarena-ai/arena-leaderboard/resolve/main/"
)
_ARENA_METADATA_FALLBACK = "leaderboard_table_20250804.csv"
_ARENA_HF_API = (
    "https://huggingface.co/api/spaces/lmarena-ai/arena-leaderboard/tree/main"
)


def _parse_arena_catalog(json_text: str) -> dict[str, float]:
    """Parse arena-catalog JSON into {model_name: elo_rating}.

    Reads only the 'full' category. Returns normalized model names as keys.
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return {}
    full = data.get("full", {})
    result = {}
    for model_name, scores in full.items():
        rating = scores.get("rating")
        if rating is not None:
            result[_normalize_model_name(model_name)] = float(rating)
    return result


def _parse_arena_metadata(csv_text: str) -> dict[str, dict]:
    """Parse arena metadata CSV into {normalized_name: {fields}}.

    Extracts knowledge_cutoff, organization, license from each row.
    """
    result = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        key = row.get("key", "").strip()
        if not key:
            continue
        cutoff = row.get("Knowledge cutoff date", "").strip()
        result[_normalize_model_name(key)] = {
            "knowledge_cutoff": cutoff if cutoff and cutoff != "-" else None,
            "organization": row.get("Organization", "").strip() or None,
            "license": row.get("License", "").strip() or None,
        }
    return result


def _discover_latest_arena_csv() -> str:
    """Find the latest leaderboard_table_YYYYMMDD.csv in the HF space.

    Falls back to a hardcoded filename on any error.
    """
    try:
        req = urllib.request.Request(_ARENA_HF_API, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            files = json.loads(resp.read())
        pattern = re.compile(r"^leaderboard_table_(\d{8})\.csv$")
        dated = []
        for f in files:
            m = pattern.match(f.get("rfilename", ""))
            if m:
                dated.append((m.group(1), f["rfilename"]))
        if dated:
            dated.sort(reverse=True)
            logger.debug("Latest arena CSV: %s", dated[0][1])
            return dated[0][1]
    except Exception as exc:
        logger.warning("Failed to discover latest arena CSV: %s", exc)
    return _ARENA_METADATA_FALLBACK


def _fetch_enrichment() -> None:
    """Fetch arena Elo and metadata, merge into annotations."""
    now = datetime.now(timezone.utc).isoformat()

    # --- Source 1: Arena Elo ratings ---
    arena_elo: dict[str, float] = {}
    try:
        req = urllib.request.Request(_ARENA_CATALOG_URL)
        with urllib.request.urlopen(req, timeout=30) as resp:
            arena_elo = _parse_arena_catalog(resp.read().decode())
        logger.info("Fetched arena Elo for %d models", len(arena_elo))
    except Exception as exc:
        logger.warning("Failed to fetch arena catalog: %s", exc)

    # --- Source 2: Arena metadata (cutoff, org, license) ---
    arena_meta: dict[str, dict] = {}
    try:
        csv_filename = _discover_latest_arena_csv()
        url = _ARENA_METADATA_BASE + csv_filename
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            arena_meta = _parse_arena_metadata(resp.read().decode())
        logger.info("Fetched arena metadata for %d models from %s", len(arena_meta), csv_filename)
    except Exception as exc:
        logger.warning("Failed to fetch arena metadata: %s", exc)

    # --- Merge into annotations ---
    all_cached_models = [m for models, _ in _model_cache.values() for m in models]
    for model_id in all_cached_models:
        entry = _annotations.setdefault(model_id, {})
        metadata = entry.setdefault("metadata", {})

        # Stamp first_seen only for newly discovered models
        if "first_seen" not in metadata:
            metadata["first_seen"] = now

        # Match arena data by normalized name — apply to ALL matching providers
        norm = _normalize_model_name(model_id)
        if norm in arena_elo:
            metadata["arena_elo"] = arena_elo[norm]
        if norm in arena_meta:
            for field in ("knowledge_cutoff", "organization", "license"):
                val = arena_meta[norm].get(field)
                if val is not None:
                    metadata[field] = val

        # Remove stale livebench_avg if present (old source is dead)
        metadata.pop("livebench_avg", None)

        metadata["last_updated"] = now

    _save_annotations(_annotations)


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------


def _resolve_model(model: str) -> tuple[str, str]:
    """Resolve a model identifier or shorthand to (full_id, api_key).

    Resolution order:
    1. Shorthand via favourites (most-used match wins)
    2. Full identifier: route directly by matching provider prefix
    3. Shorthand via all discovered models (highest Elo wins, else first alphabetically)
    """
    # Try shorthand resolution against favourites first
    favourites = _get_favourites(_annotations)
    matches = [fav for fav in favourites if fav.startswith(f"{model}/")]

    if matches:
        # Multiple matches? Pick the most-used (favourites are sorted by call_count desc)
        fav = matches[0]
        for provider, api_key in _provider_registry.items():
            if fav.startswith(f"{provider}/"):
                logger.debug("Resolved shorthand '%s' -> %s (provider=%s)", model, fav, provider)
                return fav, api_key

    # Full identifier: route directly
    if "/" in model:
        for provider, api_key in _provider_registry.items():
            if model.startswith(f"{provider}/"):
                logger.debug("Resolved full model ID '%s' (provider=%s)", model, provider)
                return model, api_key

    # Shorthand fallback: search all discovered models for the prefix
    all_models = _get_models()
    candidates = [m for m in all_models if m.startswith(f"{model}/")]
    if candidates:
        # Pick highest Elo, falling back to first alphabetically
        def _elo(m: str) -> float:
            return _annotations.get(m, {}).get("metadata", {}).get("arena_elo", 0)
        best = sorted(candidates, key=lambda m: (-_elo(m), m))[0]
        for provider, api_key in _provider_registry.items():
            if best.startswith(f"{provider}/"):
                logger.debug(
                    "Resolved shorthand '%s' -> %s via discovery (provider=%s)",
                    model, best, provider,
                )
                return best, api_key

    logger.warning("Model resolution failed for '%s'", model)
    raise ValueError(
        f"No models found matching '{model}'. "
        f"Use search_models to find valid model identifiers."
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
        "  - For a quick query, use completion with a favourite shorthand (see below).",
        "    Shorthand is a provider name (e.g. 'openai') that resolves to your",
        "    most-used model from that provider. This is not guessing — shorthands",
        "    are resolved deterministically from your usage history.",
        "  - To find any model, use search_models — results include descriptions",
        "    from the model catalog when available.",
        "  - For deep research tasks, use start_research. If it is interrupted or",
        "    times out, the task continues in the background — use check_research",
        "    to retrieve results later, or cancel_research to stop a running task.",
        "  - To generate images, use generate_image with a model like",
        "    openai/gpt-image-1 or gemini/gemini-2.5-flash-image.",
        "    Images are displayed inline and saved to disk.",
        "  - Never guess model IDs. Use search_models to find valid identifiers,",
        "    or use a favourite/shorthand listed below.",
        "Feedback:",
        "  - We'd love to hear how ask-another is working for you. Call",
        "    feedback to share issues, suggestions, or anything that felt",
        "    harder than it should be.",
        "  - If you receive confusing output or a tool call fails, consider calling",
        "    feedback to report the issue — but don't let it block your work.",
    ]
    favourites = _get_favourites(_annotations)
    unhealthy = _unhealthy_providers()
    favourites = [f for f in favourites if f.split("/")[0] not in unhealthy]
    if favourites:
        lines.append("Favourite Models:")
        for fav in favourites:
            entry = _annotations.get(fav, {})
            note = entry.get("annotations", {}).get("note", "")
            count = entry.get("usage", {}).get("call_count", 0)
            parts = [fav]
            if note:
                parts.append(note)
            parts.append(f"({count} calls made)")
            lines.append(f"  - {' — '.join(parts)}")

    rated = [
        (model_id, entry.get("metadata", {}).get("arena_elo", 0))
        for model_id, entry in _annotations.items()
        if entry.get("metadata", {}).get("arena_elo")
        and model_id.split("/")[0] not in unhealthy
    ]
    # Sort by Elo desc, then prefer direct providers (fewer path segments)
    rated.sort(key=lambda x: (-x[1], x[0].count("/"), x[0]))
    if rated:
        # Deduplicate: same model via multiple providers → keep first (most direct)
        seen_normalized: set[str] = set()
        deduped: list[tuple[str, float]] = []
        for model_id, elo in rated:
            norm = _normalize_model_name(model_id)
            if norm in seen_normalized:
                continue
            seen_normalized.add(norm)
            deduped.append((model_id, elo))
        lines.append("Top Rated Models (by Elo):")
        for model_id, elo in deduped[:5]:
            lines.append(f"  - {model_id} (Elo {elo:.0f})")

    # Surface recently added models (first_seen within last 7 days)
    recent = _get_recent_models(_annotations, days=7)
    recent = [(m, d) for m, d in recent if m.split("/")[0] not in unhealthy]
    if recent:
        # Deduplicate recently added the same way
        seen_recent: set[str] = set()
        lines.append("Recently Added:")
        count = 0
        for model_id, first_seen in recent:
            norm = _normalize_model_name(model_id)
            if norm in seen_recent:
                continue
            seen_recent.add(norm)
            lines.append(f"  - {model_id} (added {first_seen})")
            count += 1
            if count >= 5:
                break

    errors = {p: err for p, err in _provider_errors.items() if err}
    if errors:
        lines.append("Unavailable Providers:")
        for provider, err in sorted(errors.items()):
            lines.append(f"  - {provider}: {err}")

    return "\n".join(lines)


mcp = FastMCP("ask-another", instructions=_build_instructions(), lifespan=_lifespan)


def _zdr_warning(zdr: bool | None, result: str) -> str:
    """Prepend a warning if the caller is overriding the configured ZDR policy."""
    if zdr is None:
        return result
    if zdr == _zero_data_retention:
        return result
    if zdr:
        return f"⚠️ ZDR filter enabled (overriding server default of off).\n\n{result}"
    return f"⚠️ ZDR filter disabled (overriding server default of on). Some models listed may reject requests due to your provider's data retention policy.\n\n{result}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_families(
    search: str | None = None,
    zdr: bool | None = None,
) -> str:
    """Browse available provider groupings (e.g. 'openai', 'openrouter/deepseek').
    Use this to explore what's available before drilling into specific models
    with search_models.

    Args:
        search: Substring filter applied to family names
        zdr: Filter OpenRouter models to Zero Data Retention (ZDR) compatible
             only. Defaults to the server's ZERO_DATA_RETENTION setting.
             Set explicitly to override.
    """
    retry_warning = None
    if search:
        retry_warning = _retry_unhealthy_providers(search, zdr=zdr)

    all_models = _get_models(zdr=zdr)
    families = sorted(set(_get_family(m) for m in all_models))

    if search:
        families = [f for f in families if search.lower() in f.lower()]

    result = "\n".join(families)
    result = _zdr_warning(zdr, result)
    if retry_warning:
        result = f"{result}\n\n{retry_warning}" if result else retry_warning
    return result


@mcp.tool()
def search_models(
    search: str | None = None,
    zdr: bool | None = None,
) -> str:
    """Find exact model identifiers. Always call this to verify a model ID
    before passing it to completion or start_research — do not guess IDs.

    Args:
        search: Substring filter applied to full model identifiers
        zdr: Filter OpenRouter models to Zero Data Retention (ZDR) compatible
             only. Defaults to the server's ZERO_DATA_RETENTION setting.
             Set explicitly to override.
    """
    retry_warning = None
    if search:
        retry_warning = _retry_unhealthy_providers(search, zdr=zdr)

    models = _get_models(zdr=zdr)

    if search:
        models = [m for m in models if search.lower() in m.lower()]

    lines = []
    for m in models:
        entry = _annotations.get(m, {})
        note = entry.get("annotations", {}).get("note", "")
        meta = entry.get("metadata", {})
        desc_parts = []
        if meta.get("arena_elo"):
            desc_parts.append(f"Elo {meta['arena_elo']:.0f}")
        if meta.get("knowledge_cutoff"):
            desc_parts.append(f"cutoff {meta['knowledge_cutoff']}")
        if meta.get("context_length"):
            desc_parts.append(f"{meta['context_length'] // 1000}k ctx")
        if meta.get("pricing_in"):
            desc_parts.append(f"${meta['pricing_in']}/tok in")
        if note:
            desc_parts.append(note)
        if desc_parts:
            lines.append(f"{m} — {', '.join(desc_parts)}")
        else:
            lines.append(m)
    result = "\n".join(lines)
    result = _zdr_warning(zdr, result)
    if retry_warning:
        result = f"{result}\n\n{retry_warning}" if result else retry_warning
    return result


@mcp.tool()
def annotate_models(
    model: str,
    note: str,
) -> str:
    """Add or update a personal note on a model. Notes appear in search_models
    results and in the favourites list in server instructions.

    Args:
        model: Full model identifier (e.g. 'openai/gpt-5.2').
        note: Your note about this model. Overwrites any existing note.
    """
    entry = _annotations.setdefault(model, {})
    annotations = entry.setdefault("annotations", {})
    annotations["note"] = note
    _save_annotations(_annotations)
    logger.debug("Annotation saved for %s", model)
    return f"Note saved for {model}."


@mcp.tool()
def refresh_models() -> str:
    """Force a re-scan of all configured providers and re-fetch enrichment
    data from LMArena arena-catalog and LMArena metadata. Use this if
    model data seems stale or after adding a new provider.
    """
    _refresh_provider_models()
    _fetch_enrichment()
    cached_count = sum(len(models) for models, _ in _model_cache.values())
    return f"Refreshed {cached_count} models across {len(_provider_registry)} providers."


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
    )
)
def feedback(
    issue: str,
    tool_name: str | None = None,
) -> str:
    """Help us improve ask-another by sharing your experience. Call this
    whenever you're unsure how to proceed, receive confusing output, or
    a tool doesn't behave as expected. We also welcome suggestions — if
    a workflow felt more complex than it should be, if you had to guess
    at parameter values, or if something could simply work better.

    Every piece of feedback helps us make ask-another more useful.
    This tool is lightweight and safe to call at any time.

    Args:
        issue: Share what happened and what you expected. For suggestions,
               describe what could work better and why.
        tool_name: Which tool was involved, if applicable
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issue": issue,
    }
    if tool_name:
        entry["tool_name"] = tool_name

    with open(_feedback_log, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return "Feedback recorded. Thank you."


@mcp.tool()
def completion(
    model: str,
    prompt: str,
    system: str | None = None,
    temperature: float | None = None,
) -> str:
    """Call a model for a quick completion. Use this for standard prompts that
    return in seconds — use start_research instead for deep research tasks
    that need web search and source synthesis.

    Use a favourite shorthand (e.g. 'openai') or an exact model ID verified
    via search_models. Shorthands and favourite model IDs listed in the server
    instructions can be used directly without calling search_models first.

    Args:
        model: Full model identifier (e.g. 'openai/gpt-5.2') or favourite
               shorthand (e.g. 'openai' → resolves to your most-used OpenAI
               model). Use search_models to find other valid identifiers.
        prompt: The user prompt to send to the model
        system: Optional system prompt
        temperature: Sampling temperature (0.0-2.0). Omit to use model default.
                     Some models reject non-default values — omit unless needed.
    """
    import litellm
    from litellm.exceptions import AuthenticationError
    from litellm.types.utils import Choices, ModelResponse

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
        msg += " If this seems like a bug, call the feedback tool to report it."
        logger.warning("Model validation failed: %s (known: %d models)", full_model, len(known_models))
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

    logger.debug("Calling litellm.completion(model=%s)", full_model)
    try:
        response = cast(ModelResponse, litellm.completion(**kwargs))
    except AuthenticationError as exc:
        _provider_errors[provider] = str(exc)
        _provider_auth_errors.add(provider)
        logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
        raise
    logger.debug("Completion response received from %s", full_model)

    # Track usage
    _track_usage(full_model)

    choice = cast(Choices, response.choices[0])
    return choice.message.content or ""


@mcp.tool()
def generate_image(
    model: str,
    prompt: str,
    size: str | None = None,
    quality: str | None = None,
) -> list:
    """Generate an image from a text prompt. The image is returned inline
    and saved to disk (~/Pictures/ask-another by default).

    Two model types are supported — the tool picks the right path automatically:
    - Dedicated image models (gpt-image-1, dall-e-3, imagen-4): best control
      over size and quality.
    - Native image-output models (gemini-*-image / "Nano Banana"): can
      interleave text and images, good for diagrams or annotated visuals.

    Args:
        model: Model to use (e.g. 'openai/gpt-image-1',
               'gemini/gemini-2.5-flash-image'). Use search_models with
               'image' to find available image models.
        prompt: Text description of the image to generate.
        size: Image dimensions. Only used by dedicated image models — ignored
              by native image-output models. Common values: '1024x1024' (square),
              '1536x1024' (landscape), '1024x1536' (portrait). Valid options
              depend on the model. Omit to use the model's default.
        quality: Image quality. Only used by dedicated image models — ignored
                 by native image-output models. For gpt-image-1: 'low',
                 'medium', 'high'. For dall-e-3: 'standard', 'hd'. Omit for
                 the model's default.
    """
    import litellm
    from litellm.exceptions import AuthenticationError
    from litellm.types.utils import Choices, ImageResponse, ModelResponse

    from mcp.types import ImageContent, TextContent

    full_model, api_key = _resolve_model(model)
    provider = full_model.split("/")[0]

    if _is_native_image_model(full_model):
        # Completion path with image modalities (Nano Banana, etc.)
        kwargs: dict = {
            "model": full_model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "api_key": api_key,
            "timeout": 120,
        }
        logger.debug(
            "Calling litellm.completion(model=%s, modalities=[image,text])",
            full_model,
        )
        try:
            response = cast(ModelResponse, litellm.completion(**kwargs))
        except AuthenticationError as exc:
            _provider_errors[provider] = str(exc)
            _provider_auth_errors.add(provider)
            logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
            raise
        logger.debug("Image completion response received from %s", full_model)

        if not response.choices:
            raise ValueError(
                f"Model {full_model} returned no response choices "
                "(likely filtered by safety policy). Try rephrasing the prompt."
            )

        result_blocks: list = []

        choice = cast(Choices, response.choices[0])
        text: str | None = choice.message.content
        if text:
            result_blocks.append(TextContent(type="text", text=text))

        images: list = getattr(choice.message, "images", None) or []
        if not images:
            raise ValueError(
                f"Model {full_model} returned no images. "
                "Try making the image request more explicit in your prompt."
            )

        for img_item in images:
            url = img_item["image_url"]["url"]
            b64_data, mime_type = _extract_image_b64(None, url)
            filepath = _save_image(b64_data, mime_type, prompt)
            logger.debug("Image saved to %s", filepath)
            result_blocks.append(
                ImageContent(type="image", data=b64_data, mimeType=mime_type)
            )
            result_blocks.append(
                TextContent(type="text", text=f"Saved to: {filepath}")
            )

        return result_blocks

    # Dedicated image generation API (gpt-image-1, dall-e-3, imagen, etc.)
    kwargs = {
        "prompt": prompt,
        "model": full_model,
        "n": 1,
        "api_key": api_key,
        "timeout": 120,
    }
    if size is not None:
        kwargs["size"] = size
    if quality is not None:
        kwargs["quality"] = quality

    logger.debug("Calling litellm.image_generation(model=%s)", full_model)
    try:
        response = cast(ImageResponse, litellm.image_generation(**kwargs))
    except AuthenticationError as exc:
        _provider_errors[provider] = str(exc)
        _provider_auth_errors.add(provider)
        logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
        raise
    logger.debug("Image generation response received from %s", full_model)

    if not response.data:
        raise ValueError(f"Model {full_model} returned no image data.")
    img_obj = response.data[0]
    b64_data, mime_type = _extract_image_b64(
        getattr(img_obj, "b64_json", None),
        getattr(img_obj, "url", None),
    )
    filepath = _save_image(b64_data, mime_type, prompt)
    logger.debug("Image saved to %s", filepath)

    result_blocks = []
    revised = getattr(img_obj, "revised_prompt", None)
    if revised:
        result_blocks.append(
            TextContent(type="text", text=f"Revised prompt: {revised}")
        )
    result_blocks.append(
        ImageContent(type="image", data=b64_data, mimeType=mime_type)
    )
    result_blocks.append(
        TextContent(type="text", text=f"Saved to: {filepath}")
    )
    return result_blocks


def _get_job_store(ctx: Context | None) -> JobStore:
    """Extract the JobStore from a tool's Context."""
    if ctx is None:
        raise RuntimeError("Context required for research operations")
    return ctx.request_context.lifespan_context["job_store"]


def _is_openai_research(model: str) -> bool:
    """Check if a model needs web_search_preview tools for research."""
    return model.startswith("openai/") and "deep-research" in model


# ---------------------------------------------------------------------------
# Image generation helpers
# ---------------------------------------------------------------------------

_NATIVE_IMAGE_PATTERNS = (
    "gemini-2.0-flash-exp-image",
    "gemini-2.5-flash-image",
    "gemini-3-pro-image",
    "gemini-3.1-flash-image",
)


def _is_native_image_model(model: str) -> bool:
    """True if model generates images via completion with modalities,
    False if it uses the dedicated image_generation API."""
    return any(pat in model for pat in _NATIVE_IMAGE_PATTERNS)


def _extract_image_b64(
    b64_json: str | None,
    url: str | None,
) -> tuple[str, str]:
    """Normalise image data from LiteLLM into (base64_data, mime_type).

    Handles three formats:
    - b64_json: raw base64 string (from image_generation response_format="b64_json")
    - data URL: "data:image/png;base64,..." (from completion modalities)
    - HTTP URL: fetch and base64-encode (fallback for url-only responses)
    """
    if b64_json:
        return b64_json, "image/png"

    if url:
        if url.startswith("data:"):
            header, b64 = url.split(",", 1)
            mime = header.split(":")[1].split(";")[0]
            return b64, mime
        # HTTP URL — fetch it
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "image/png")
        return base64.b64encode(raw).decode(), content_type

    raise ValueError("No image data in response")


def _save_image(b64_data: str, mime_type: str, prompt: str) -> Path:
    """Save base64 image data to disk and return the file path.

    Images are saved to IMAGE_OUTPUT_DIR (default: ~/Pictures/ask-another/).
    Filenames are timestamp-based with a slugified prompt prefix.
    """
    output_dir = Path(
        os.path.expanduser(
            os.environ.get("IMAGE_OUTPUT_DIR", "~/Pictures/ask-another")
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(mime_type, ".png")

    slug = re.sub(r"[^a-z0-9]+", "-", prompt[:40].lower()).strip("-")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{slug}{ext}"

    filepath = output_dir / filename
    filepath.write_bytes(base64.b64decode(b64_data))

    return filepath


def _run_research_completion_sync(job: ResearchJob, api_key: str) -> None:
    """Execute a research task via litellm.completion (blocking)."""
    import litellm
    from litellm.exceptions import AuthenticationError
    from litellm.types.utils import Choices, ModelResponse

    kwargs: dict[str, Any] = {
        "model": job.model,
        "messages": [{"role": "user", "content": job.query}],
        "api_key": api_key,
        "timeout": 1800,
    }

    # OpenAI deep research models need web_search_preview tool
    if _is_openai_research(job.model):
        kwargs["tools"] = [{"type": "web_search_preview"}]

    logger.info("Research job %d starting: model=%s", job.job_id, job.model)
    try:
        response = cast(ModelResponse, litellm.completion(**kwargs))
        choice = cast(Choices, response.choices[0])
        job.result = choice.message.content
        job.citations = getattr(response, "citations", []) or []
        job.status = "completed"
        logger.info("Research job %d completed", job.job_id)
    except AuthenticationError as exc:
        provider = job.model.split("/")[0]
        _provider_errors[provider] = str(exc)
        _provider_auth_errors.add(provider)
        logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
        job.status = "failed"
        job.error = str(exc)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        logger.warning("Research job %d failed: %s", job.job_id, exc)
    finally:
        job.ended = datetime.now(timezone.utc).strftime("%H:%M")


async def _run_research_completion(job: ResearchJob, api_key: str) -> None:
    """Run the blocking completion in a thread to avoid blocking the event loop."""
    await anyio.to_thread.run_sync(lambda: _run_research_completion_sync(job, api_key))


def _run_research_gemini_sync(job: ResearchJob, api_key: str) -> None:
    """Execute a research task via Gemini Interactions API (blocking poll loop)."""
    import litellm.interactions
    from litellm.exceptions import AuthenticationError
    from litellm.types.interactions import InteractionsAPIResponse

    agent_name = job.model.split("/", 1)[1]  # strip "gemini/" prefix

    logger.info("Gemini research job %d starting: agent=%s", job.job_id, agent_name)
    try:
        response = cast(InteractionsAPIResponse, litellm.interactions.create(
            agent=agent_name,
            input=job.query,
            background=True,
            api_key=api_key,
        ))
        interaction_id = response.id or ""
        logger.debug("Gemini interaction created: id=%s", interaction_id)

        # Poll until complete or failed
        while True:
            status_resp = cast(InteractionsAPIResponse, litellm.interactions.get(
                interaction_id=interaction_id,
                api_key=api_key,
            ))
            logger.debug("Gemini poll: status=%s", status_resp.status)
            if status_resp.status == "completed":
                outputs = status_resp.outputs or []
                if outputs:
                    last = outputs[-1]
                    job.result = last.get("text", "") if isinstance(last, dict) else getattr(last, "text", "")
                    annotations = last.get("annotations", []) if isinstance(last, dict) else getattr(last, "annotations", [])
                    job.citations = [
                        a.get("source", "") if isinstance(a, dict) else getattr(a, "source", "")
                        for a in (annotations or [])
                    ]
                job.status = "completed"
                logger.info("Gemini research job %d completed", job.job_id)
                return
            elif status_resp.status in ("failed", "cancelled"):
                job.status = "failed"
                job.error = getattr(status_resp, "error", "Unknown error")
                logger.warning("Gemini research job %d %s: %s", job.job_id, status_resp.status, job.error)
                return

            time.sleep(10)

    except AuthenticationError as exc:
        provider = job.model.split("/")[0]
        _provider_errors[provider] = str(exc)
        _provider_auth_errors.add(provider)
        logger.warning("Auth failed for %s, provider marked unhealthy: %s", provider, exc)
        job.status = "failed"
        job.error = str(exc)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        logger.warning("Gemini research job %d failed: %s", job.job_id, exc)
    finally:
        job.ended = datetime.now(timezone.utc).strftime("%H:%M")


async def _run_research_gemini(job: ResearchJob, api_key: str) -> None:
    """Run the Gemini Interactions API polling in a thread."""
    await anyio.to_thread.run_sync(lambda: _run_research_gemini_sync(job, api_key))


def _is_gemini_deep_research(model: str) -> bool:
    """Check if a model ID is a Gemini deep research agent."""
    return model.startswith("gemini/deep-research")


@mcp.tool()
async def start_research(
    model: str,
    query: str,
    timeout: int = 300,
    ctx: Context | None = None,
) -> str:
    """Start a deep research task. This submits a research query to a model
    that will search the web, read sources, and synthesize a cited report.

    Research tasks can take minutes to complete. This tool will wait for
    results and return them directly if the task finishes in time. If it
    is interrupted or the task times out, the research continues in the
    background — use check_research to retrieve results later.

    Args:
        model: Model to use (e.g. 'openrouter/perplexity/sonar-deep-research').
               Use search_models with 'deep-research' to find available models.
        query: The research question or topic to investigate.
        timeout: Max seconds to wait for results (default 300). If exceeded,
                 the task continues in the background.
    """
    full_model, api_key = _resolve_model(model)
    job_store = _get_job_store(ctx)
    job = job_store.create_job(model=full_model, query=query)

    # Pick the right research path
    if _is_gemini_deep_research(full_model):
        research_fn = _run_research_gemini
    else:
        research_fn = _run_research_completion

    # Spawn the research task in the background task group
    cancel_scope = anyio.CancelScope()
    job._task_scope = cancel_scope

    async def _wrapped_task() -> None:
        with cancel_scope:
            await research_fn(job, api_key)

    job_store.task_group.start_soon(_wrapped_task)

    # Wait for results or timeout, handling interruption gracefully
    try:
        deadline = time.time() + timeout
        while job.status == "in_progress":
            if time.time() >= deadline:
                return (
                    f"Research is still running (job_id={job.job_id}). "
                    f"Use check_research to retrieve results later, "
                    f"or cancel_research to stop it."
                )
            await anyio.sleep(2)

    except (asyncio.CancelledError, anyio.get_cancelled_exc_class()):
        # User hit escape — job continues in background
        raise

    if job.status == "completed":
        result: dict[str, Any] = {"report": job.result}
        if job.citations:
            result["citations"] = job.citations
        return json.dumps(result)

    return f"Research failed (job_id={job.job_id}): {job.error}"


@mcp.tool()
async def check_research(
    job_id: int | None = None,
    ctx: Context | None = None,
) -> str:
    """Check on research tasks started with start_research.

    Called with no arguments, returns a table of all research tasks with
    their job_id, model, status, query, and timing.
    Called with a job_id, returns the full results of a completed task
    including the research report and cited sources.

    Use this after start_research was interrupted or timed out, or to
    poll a long-running task.

    Args:
        job_id: A specific job to retrieve. Omit to list all jobs.
    """
    job_store = _get_job_store(ctx)

    if job_id is not None:
        job = job_store.get_job(job_id)
        if not job:
            return f"No job found with job_id={job_id}. Use check_research with no arguments to list all jobs."

        if job.status == "in_progress":
            return f"Job {job.job_id} is still in progress (started {job.started})."

        if job.status == "completed":
            result: dict[str, Any] = {"report": job.result}
            if job.citations:
                result["citations"] = job.citations
            return json.dumps(result)

        return f"Job {job.job_id} {job.status}: {job.error}" if job.error else f"Job {job.job_id} {job.status}."

    # List all jobs as markdown table
    jobs = job_store.all_jobs()
    if not jobs:
        return "No research tasks found."

    lines = [
        "| job_id | model | status | query | started | ended |",
        "|--------|-------|--------|-------|---------|-------|",
    ]
    for j in jobs:
        q = j.query[:50] + "\u2026" if len(j.query) > 50 else j.query
        lines.append(
            f"| {j.job_id} | {j.model} | {j.status} | {q} | {j.started} | {j.ended} |"
        )
    return "\n".join(lines)


@mcp.tool()
async def cancel_research(
    job_id: int,
    ctx: Context | None = None,
) -> str:
    """Cancel a running research task. Use check_research first to find
    the job_id of the task you want to cancel.

    Args:
        job_id: The job to cancel.
    """
    job_store = _get_job_store(ctx)
    job = job_store.get_job(job_id)

    if not job:
        return f"No job found with job_id={job_id}."

    if job.status != "in_progress":
        return f"Job {job_id} is already {job.status}."

    if job._task_scope:
        job._task_scope.cancel()
    job.status = "cancelled"
    job.ended = datetime.now(timezone.utc).strftime("%H:%M")
    return f"Job {job_id} cancelled."


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
