# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An MCP (Model Context Protocol) server that lets Claude Desktop query other LLMs through a unified interface. It uses LiteLLM as the multi-provider backend and FastMCP for the server framework. Providers are configured via environment variables, and models are discovered dynamically via provider APIs.

## Commands

```bash
uv sync                                                                    # Install dependencies
PROVIDER_OPENAI="sk-test" uv run ask-another                               # Run the server locally
```

Tests can be run with:

```bash
uv run --with pytest python -m pytest tests/ -v
```

## Architecture

The entire server lives in a single file: `src/ask_another/server.py`. It exposes these MCP tools:

- **`search_families`** — discovers model families across configured providers, with optional substring search
- **`search_models`** — finds specific model identifiers with optional substring search; enriches results with metadata (Elo, knowledge cutoff, context length, pricing, notes) from the annotations file
- **`completion`** — proxies a completion request to a specified LLM via LiteLLM, supports full model identifiers or favourite shorthand; tracks usage in the annotations file
- **`annotate_models`** — adds or updates a personal note on a model; notes appear in search results and server instructions
- **`refresh_models`** — force re-scan of all providers and re-fetch benchmark data from LMArena arena-catalog (GitHub JSON) and LMArena metadata (HuggingFace CSV)
- **`feedback`** — collects usability issues from the LLM client into a JSONL log file (`~/.ask-another-feedback.jsonl` by default, configurable via `FEEDBACK_LOG` env var)
- **`start_research`** — starts a deep research task that runs in the background via a lifespan task group. Supports two paths: OpenRouter (Perplexity/OpenAI via `litellm.completion`) and Gemini deep research (via `litellm.interactions.create` with polling). Blocks until results arrive or timeout, then returns results or a job handle. If interrupted (user hits escape), the research continues in the background.
- **`check_research`** — lists all research jobs as a markdown table, or retrieves full results for a specific job_id
- **`cancel_research`** — cancels a running research task by its job_id
- **`generate_image`** — generates an image from a text prompt. Automatically routes between two LiteLLM paths: `litellm.image_generation()` for dedicated image models (gpt-image-1, dall-e-3, imagen-4) and `litellm.completion()` with `modalities=["image","text"]` for native image-output models (Gemini Nano Banana family). Returns images inline via MCP `ImageContent` and saves to disk.

Providers are configured via `PROVIDER_*` environment variables. Two formats are accepted: bare key (`PROVIDER_OPENAI=sk-...`, provider derived from var suffix) or legacy prefixed (`PROVIDER_OPENAI=openai;sk-...`, prefix wins). These are parsed at module import time into a `_provider_registry` dict mapping provider names to API keys.

Model discovery uses `litellm.get_valid_models(check_provider_endpoint=True)` by default, with exception handlers for providers where LiteLLM listing is unsupported (OpenRouter). A generic normalisation rule ensures all model IDs use `provider/model-name` format. Results are cached in memory with a configurable TTL.

### Annotations System

`~/.ask-another-annotations.json` (configurable via `ANNOTATIONS_FILE` env var) is the single source of truth for model metadata, usage data, and personal notes. Schema:

```json
{
  "openai/gpt-5.2": {
    "metadata": {
      "arena_elo": 1486,
      "knowledge_cutoff": "2025/6",
      "organization": "OpenAI",
      "license": "Proprietary",
      "first_seen": "2026-01-15T08:00:00Z",
      "last_updated": "2026-03-12T10:30:00Z"
    },
    "usage": {
      "call_count": 47,
      "last_used": "2026-03-12T14:20:00Z"
    },
    "annotations": {
      "note": "Fast, good for code review"
    }
  }
}
```

- **Favourites** are derived automatically from the top 5 models by `usage.call_count`. No configuration needed — just use the MCP and favourites emerge from actual usage.
- **Notes** are set via the `annotate_models` tool. They appear in search results and server instructions.
- **Metadata** is populated automatically on startup: the server scans all providers for available models, then fetches Elo ratings from LMArena arena-catalog (GitHub JSON) and knowledge cutoff dates/org/license from LMArena metadata (HuggingFace CSV). OpenRouter models additionally get pricing and context length from the OpenRouter API. `first_seen` is stamped when a model is first discovered.
- **Refresh** happens automatically when `metadata.last_updated` exceeds the TTL (`CACHE_TTL_MINUTES`, default 360 = 6 hours). Can also be triggered manually via `refresh_models`.

### Debug Logging

File-based debug logging can be enabled via environment variables. When disabled (default), no handlers are attached and there is zero overhead.

| Var | Default | Notes |
|-----|---------|-------|
| `LOG_LEVEL` | (empty = disabled) | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `~/.ask-another.log` | Path to log file |
| `LOG_FILE_SIZE` | `5` | Max file size in MB |
| `LOG_FILE_COUNT` | `2` | Number of backup files to keep |
| `IMAGE_OUTPUT_DIR` | `~/Pictures/ask-another` | Directory for saved generated images |

Uses `RotatingFileHandler` — files rotate at `LOG_FILE_SIZE` MB, keeping `LOG_FILE_COUNT` backups (e.g. `.log`, `.log.1`, `.log.2`).

The entrypoint is `ask_another.server:main` (defined in `pyproject.toml` `[project.scripts]`), which calls `mcp.run()` on the FastMCP instance.

## Key Dependencies

- **mcp** (FastMCP) — MCP server framework
- **litellm** — unified LLM API client (imported lazily inside tools)
- **uv** — package manager (Python >=3.10)
