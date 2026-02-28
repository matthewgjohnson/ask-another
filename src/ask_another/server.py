"""MCP server implementation for ask-another v2."""

from __future__ import annotations

import asyncio
import logging
import json
import os
import re
import time
import urllib.request
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import anyio
from mcp.server.fastmcp import Context, FastMCP

# Provider registry: {provider_name: api_key}
_provider_registry: dict[str, str] = {}

# Favourites: list of full model identifiers
_favourites: list[str] = []

# Cache: {provider_name: (model_ids, timestamp)}
_model_cache: dict[str, tuple[list[str], float]] = {}

# Cache TTL in seconds (default 6 hours)
_cache_ttl: int = 21600

# Whether to filter OpenRouter models to ZDR-compatible only (default: on)
_zero_data_retention: bool = True


@dataclass(frozen=True)
class ModelMeta:
    """Metadata for a model from the PSV catalog."""

    model_id: str
    favourite: bool
    description: str


# Model catalog: {model_id: ModelMeta}
_model_catalog: dict[str, ModelMeta] = {}

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
    result: str = ""
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
async def _lifespan(server: FastMCP) -> Any:
    """Lifespan context providing a task group and job store."""
    async with anyio.create_task_group() as tg:
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


def _load_psv() -> dict[str, ModelMeta]:
    """Load the model catalog from a PSV file.

    Looks for the file at: MODELS_PSV env var, then next to this module.
    Uses anchor-on-ends parsing: parts[0]=model_id, parts[-1]=description,
    parts[-2]=favourite flag. Robust to column count changes.
    """
    psv_path_str = os.environ.get("MODELS_PSV", "")
    if psv_path_str:
        psv_path = Path(psv_path_str)
    else:
        psv_path = Path(__file__).parent / "models.psv"

    if not psv_path.is_file():
        logger.debug("No PSV catalog found at %s", psv_path)
        return {}

    catalog: dict[str, ModelMeta] = {}
    for line in psv_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("model|"):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        model_id = parts[0]
        description = parts[-1]
        favourite = parts[-2].lower() == "yes" if len(parts) >= 2 else False
        catalog[model_id] = ModelMeta(
            model_id=model_id, favourite=favourite, description=description
        )
    return catalog


def _load_config() -> None:
    """Scan environment and populate provider registry, favourites, and cache TTL."""
    global _provider_registry, _favourites, _cache_ttl, _model_catalog, _zero_data_retention

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

    _model_catalog = _load_psv()

    zdr_val = os.environ.get("ZERO_DATA_RETENTION", "").lower()
    if zdr_val:
        _zero_data_retention = zdr_val in ("1", "true", "yes")
    else:
        _zero_data_retention = True

    # Bootstrap favourites from PSV if FAVOURITES env var is empty
    if not _favourites and _model_catalog:
        _favourites = [
            meta.model_id for meta in _model_catalog.values() if meta.favourite
        ]


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------


def _normalise_model_id(model_id: str, provider: str) -> str:
    """Ensure a model ID has the provider prefix."""
    if not model_id.startswith(f"{provider}/"):
        return f"{provider}/{model_id}"
    return model_id


def _fetch_openrouter_models(api_key: str, *, zdr: bool = False) -> list[str]:
    """Fetch models from OpenRouter's API directly.

    When zdr is True, fetches from the ZDR endpoint which returns only
    models compatible with Zero Data Retention.
    """
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
        # ZDR endpoint returns endpoints with model_id; deduplicate
        seen: set[str] = set()
        models: list[str] = []
        for endpoint in data.get("data", []):
            model_id = endpoint.get("model_id", "")
            if model_id and model_id not in seen:
                seen.add(model_id)
                models.append(f"openrouter/{model_id}")
        return models

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return [f"openrouter/{m['id']}" for m in data.get("data", [])]


def _fetch_models(provider: str, api_key: str, *, zdr: bool = False) -> list[str]:
    """Fetch the model list for a provider."""
    if provider == "openrouter":
        return _fetch_openrouter_models(api_key, zdr=zdr)

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

        cache_key = f"{p}:zdr={effective_zdr}" if p == "openrouter" else p

        if cache_key in _model_cache:
            cached_models, cached_at = _model_cache[cache_key]
            if now - cached_at < _cache_ttl:
                all_models.extend(cached_models)
                continue

        try:
            models = _fetch_models(p, _provider_registry[p], zdr=effective_zdr)
            if models:
                _model_cache[cache_key] = (models, now)
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
        "  - For a quick query, use completion with a favourite shorthand (see below).",
        "  - To find any model, use search_models — results include descriptions",
        "    from the model catalog when available.",
        "  - For deep research tasks, use start_research. If it is interrupted or",
        "    times out, the task continues in the background — use check_research",
        "    to retrieve results later, or cancel_research to stop a running task.",
        "  - Never guess model IDs.",
        "Feedback:",
        "  - We'd love to hear how ask-another is working for you. Call",
        "    feedback to share issues, suggestions, or anything that felt",
        "    harder than it should be.",
        "  - Call feedback before retrying if you receive confusing output",
        "    or a tool call fails — it helps us improve.",
    ]
    if _favourites:
        lines.append("Favourite Models:")
        for fav in _favourites:
            meta = _model_catalog.get(fav)
            if meta and meta.description:
                lines.append(f"  - {fav} — {meta.description}")
            else:
                lines.append(f"  - {fav}")
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
        zdr: Filter OpenRouter models to ZDR-compatible only. Defaults to
             the server's ZERO_DATA_RETENTION setting. Set explicitly to
             override.
    """
    all_models = _get_models(zdr=zdr)
    families = sorted(set(_get_family(m) for m in all_models))

    if search:
        families = [f for f in families if search.lower() in f.lower()]

    result = "\n".join(families)
    return _zdr_warning(zdr, result)


@mcp.tool()
def search_models(
    search: str | None = None,
    zdr: bool | None = None,
) -> str:
    """Find exact model identifiers. Always call this to verify a model ID
    before passing it to completion or start_research — do not guess IDs.

    Args:
        search: Substring filter applied to full model identifiers
        zdr: Filter OpenRouter models to ZDR-compatible only. Defaults to
             the server's ZERO_DATA_RETENTION setting. Set explicitly to
             override.
    """
    models = _get_models(zdr=zdr)

    if search:
        models = [m for m in models if search.lower() in m.lower()]

    lines = []
    for m in models:
        meta = _model_catalog.get(m)
        if meta and meta.description:
            lines.append(f"{m} — {meta.description}")
        else:
            lines.append(m)
    result = "\n".join(lines)
    return _zdr_warning(zdr, result)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
    }
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
    return in seconds — use start_research instead for deep research tasks.
    Use a favourite shorthand (e.g. 'openai') or an exact model ID verified
    via search_models. Do not set temperature unless you have a specific
    reason — some models reject non-default values.

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
        msg += " If this seems like a bug, call the feedback tool to report it."
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


def _get_job_store(ctx: Context) -> JobStore:
    """Extract the JobStore from a tool's Context."""
    return ctx.request_context.lifespan_context["job_store"]


def _is_openai_research(model: str) -> bool:
    """Check if a model needs web_search_preview tools for research."""
    return model.startswith("openai/") and "deep-research" in model


def _run_research_completion_sync(job: ResearchJob, api_key: str) -> None:
    """Execute a research task via litellm.completion (blocking)."""
    import litellm

    kwargs: dict[str, Any] = {
        "model": job.model,
        "messages": [{"role": "user", "content": job.query}],
        "api_key": api_key,
        "timeout": 1800,
    }

    # OpenAI deep research models need web_search_preview tool
    if _is_openai_research(job.model):
        kwargs["tools"] = [{"type": "web_search_preview"}]

    try:
        response = litellm.completion(**kwargs)
        job.result = response.choices[0].message.content
        job.citations = getattr(response, "citations", []) or []
        job.status = "completed"
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
    finally:
        job.ended = datetime.now(timezone.utc).strftime("%H:%M")


async def _run_research_completion(job: ResearchJob, api_key: str) -> None:
    """Run the blocking completion in a thread to avoid blocking the event loop."""
    await anyio.to_thread.run_sync(lambda: _run_research_completion_sync(job, api_key))


def _run_research_gemini_sync(job: ResearchJob, api_key: str) -> None:
    """Execute a research task via Gemini Interactions API (blocking poll loop)."""
    import litellm.interactions

    agent_name = job.model.split("/", 1)[1]  # strip "gemini/" prefix

    try:
        response = litellm.interactions.create(
            agent=agent_name,
            input=job.query,
            background=True,
            api_key=api_key,
        )
        interaction_id = response.id

        # Poll until complete or failed
        while True:
            status_resp = litellm.interactions.get(
                interaction_id=interaction_id,
                api_key=api_key,
            )
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
                return
            elif status_resp.status in ("failed", "cancelled"):
                job.status = "failed"
                job.error = getattr(status_resp, "error", "Unknown error")
                return

            time.sleep(10)

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
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
    ctx: Context = None,
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
    ctx: Context = None,
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
    ctx: Context = None,
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
