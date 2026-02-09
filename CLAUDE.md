# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An MCP (Model Context Protocol) server that lets Claude Desktop query other LLMs through a unified interface. It uses LiteLLM as the multi-provider backend and FastMCP for the server framework. Providers are configured via environment variables, and models are discovered dynamically via provider APIs.

## Commands

```bash
uv sync                                                                    # Install dependencies
PROVIDER_OPENAI="openai;sk-test" uv run ask-another                        # Run the server locally
```

There are no tests or linting configured yet.

## Architecture

The entire server lives in a single file: `src/ask_another/server.py`. It exposes two MCP tools:

- **`list_models`** — discovers available models from configured providers, with optional provider filter and favourites-only mode
- **`completion`** — proxies a completion request to a specified LLM via LiteLLM, supports full model identifiers or favourite shorthand

Providers are configured via `PROVIDER_*` environment variables with the format `provider-name;api-key`. These are parsed at module import time into a `_provider_registry` dict mapping provider names to API keys.

Model discovery uses `litellm.get_valid_models(check_provider_endpoint=True)` by default, with exception handlers for providers where LiteLLM listing is unsupported (OpenRouter). A generic normalisation rule ensures all model IDs use `provider/model-name` format. Results are cached in memory with a configurable TTL.

Favourites (`FAVOURITES` env var) enable shorthand resolution: passing `openai` to completion resolves to the configured OpenAI favourite.

The entrypoint is `ask_another.server:main` (defined in `pyproject.toml` `[project.scripts]`), which calls `mcp.run()` on the FastMCP instance.

## Key Dependencies

- **mcp** (FastMCP) — MCP server framework
- **litellm** — unified LLM API client (imported lazily inside tools)
- **uv** — package manager (Python >=3.10)
