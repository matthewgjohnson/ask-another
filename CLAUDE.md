# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An MCP (Model Context Protocol) server that lets Claude Desktop query other LLMs through a unified interface. It uses LiteLLM as the multi-provider backend and FastMCP for the server framework. Providers are configured via environment variables, and models are discovered dynamically via provider APIs.

## Commands

```bash
uv sync                                                                    # Install dependencies
PROVIDER_OPENAI="openai;sk-test" uv run ask-another                        # Run the server locally
```

Tests can be run with:

```bash
uv run --with pytest python -m pytest tests/ -v
```

## Architecture

The entire server lives in a single file: `src/ask_another/server.py`. It exposes these MCP tools:

- **`search_families`** — discovers model families across configured providers, with optional substring search
- **`search_models`** — finds specific model identifiers with optional substring search; enriches results with descriptions from the PSV model catalog
- **`feedback`** — collects usability issues from the LLM client into a JSONL log file (`~/.ask-another-feedback.jsonl` by default, configurable via `FEEDBACK_LOG` env var)
- **`completion`** — proxies a completion request to a specified LLM via LiteLLM, supports full model identifiers or favourite shorthand
- **`start_research`** — starts a deep research task that runs in the background via a lifespan task group. Supports two paths: OpenRouter (Perplexity/OpenAI via `litellm.completion`) and Gemini deep research (via `litellm.interactions.create` with polling). Blocks until results arrive or timeout, then returns results or a job handle. If interrupted (user hits escape), the research continues in the background.
- **`check_research`** — lists all research jobs as a markdown table, or retrieves full results for a specific job_id
- **`cancel_research`** — cancels a running research task by its job_id

Providers are configured via `PROVIDER_*` environment variables with the format `provider-name;api-key`. These are parsed at module import time into a `_provider_registry` dict mapping provider names to API keys.

Model discovery uses `litellm.get_valid_models(check_provider_endpoint=True)` by default, with exception handlers for providers where LiteLLM listing is unsupported (OpenRouter). A generic normalisation rule ensures all model IDs use `provider/model-name` format. Results are cached in memory with a configurable TTL.

Favourites (`FAVOURITES` env var) enable shorthand resolution: passing `openai` to completion resolves to the configured OpenAI favourite. When `FAVOURITES` is not set, favourites are bootstrapped from the PSV model catalog (see below).

### Model Catalog (PSV)

`src/ask_another/models.psv` ships with the package as the default model catalog. It's a pipe-separated file produced by the `/research-models` skill (canonical source: `docs/models.psv`). The catalog provides:

- **Favourite bootstrapping**: when `FAVOURITES` env var is empty, models marked `favourite=yes` in the PSV are used
- **Descriptions in instructions**: server instructions show `model_id — description` for each favourite, helping the LLM client choose
- **Enriched search**: `search_models` includes descriptions from the catalog for every matching model

Override the PSV path with the `MODELS_PSV` env var (useful for development: point at `docs/models.psv` directly). If the file is missing, the server degrades gracefully — no favourites, no descriptions.

### Debug Logging

File-based debug logging can be enabled via environment variables. When disabled (default), no handlers are attached and there is zero overhead.

| Var | Default | Notes |
|-----|---------|-------|
| `LOG_LEVEL` | (empty = disabled) | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `~/.ask-another.log` | Path to log file |
| `LOG_FILE_SIZE` | `5` | Max file size in MB |
| `LOG_FILE_COUNT` | `2` | Number of backup files to keep |

Uses `RotatingFileHandler` — files rotate at `LOG_FILE_SIZE` MB, keeping `LOG_FILE_COUNT` backups (e.g. `.log`, `.log.1`, `.log.2`).

The entrypoint is `ask_another.server:main` (defined in `pyproject.toml` `[project.scripts]`), which calls `mcp.run()` on the FastMCP instance.

## Key Dependencies

- **mcp** (FastMCP) — MCP server framework
- **litellm** — unified LLM API client (imported lazily inside tools)
- **uv** — package manager (Python >=3.10)
