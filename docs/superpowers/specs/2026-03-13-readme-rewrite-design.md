# README Rewrite — Hub-and-Spoke Documentation

**Date:** 2026-03-13
**Status:** Approved
**Scope:** Replace the current README with a lean landing page + two linked docs

## Problem

The current README (111 lines) is outdated:
- Documents 4 of 10 tools
- References removed `FAVOURITES` env var
- Uses old `CACHE_TTL` name (now `CACHE_TTL_MINUTES`)
- macOS only (no Linux/Windows)
- Claude Desktop only (no Claude Code, Cursor, Windsurf, Cline, Zed)
- No mention of annotations, enrichment, research, or image generation

## Design Decisions

- **Hub-and-spoke structure** — README is a landing page (~60-80 lines), links to two detail docs
- **Audience** — primarily users (install, configure, go), secondarily contributors
- **uv install** — platform package managers only (brew/apt/winget), no curl|bash patterns
- **Client configs** — Claude Desktop + Claude Code in detail; Cursor, Windsurf, Cline, Zed in collapsible sections in install doc
- **Tool docs** — grouped by purpose, one-liner + params each
- **Config** — all options documented as what they are: entries in the MCP client's env block

## File Structure

| File | Purpose | Est. lines |
|------|---------|-----------|
| `README.md` | Landing page + quick start + usage examples + links | ~60-80 |
| `docs/install.md` | uv install, all client configs, all config options | ~150-180 |
| `docs/reference.md` | Tools, annotations/enrichment, architecture, development | ~200-250 |

## README.md

### Title + Description

```markdown
# ask-another

An MCP server that gives your AI assistant access to other LLMs. Query hundreds
of models across OpenAI, Google, and OpenRouter through a single interface — with
model discovery, usage-based favourites, and automatic enrichment (Elo ratings,
pricing, knowledge cutoffs).
```

### Quick Start

1. Install uv — show `brew install uv` (link to install doc for other platforms)
2. Add JSON config to Claude Desktop (show full snippet with `PROVIDER_*` env vars, macOS path)
3. Restart Claude Desktop

The JSON config snippet:

```json
{
  "mcpServers": {
    "ask-another": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
      "env": {
        "PROVIDER_OPENAI": "openai;sk-your-openai-key",
        "PROVIDER_GEMINI": "gemini;your-google-key",
        "PROVIDER_OPENROUTER": "openrouter;sk-or-your-openrouter-key"
      }
    }
  }
}
```

Note: at least one provider is required. Remove any you don't have keys for.

### What You Can Do

Usage examples showing natural language → tool mapping:

- "Ask GPT-5.2 what it thinks about this architecture" → `completion`
- "What Gemini models are available?" → `search_models`
- "Research the state of WebAssembly in 2026" → `start_research`
- "Generate a logo for my project" → `generate_image`
- "Note that DeepSeek is good for creative writing" → `annotate_models`

### Learn More

Links to the two docs:

- **Installation Guide** (`docs/install.md`) — platform-specific uv setup, all MCP client configs, configuration options
- **Reference** (`docs/reference.md`) — tools, annotations & enrichment, architecture, development

### License

MIT

## docs/install.md

### Install uv

Three platform commands, no curl|bash:

```
macOS:    brew install uv
Linux:    apt install uv
Windows:  winget install astral-sh.uv
```

Link to [uv docs](https://docs.astral.sh/uv/) for alternative install methods.

### Client Setup

#### Claude Desktop (macOS / Windows)

Config paths:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Full JSON snippet (same as README quick start).

#### Claude Code (CLI)

```bash
claude mcp add ask-another \
  uvx --from git+https://github.com/matthewgjohnson/ask-another ask-another \
  -e PROVIDER_OPENAI="openai;sk-your-key" \
  -e PROVIDER_GEMINI="gemini;your-key" \
  -e PROVIDER_OPENROUTER="openrouter;sk-or-your-key"
```

#### Other Clients

Collapsible `<details>` sections for each:

- **Cursor** — Settings > Features > MCP > Add New MCP Server. Provide the command and args.
- **Windsurf** — Edit `~/.codeium/windsurf/mcp_config.json` with same JSON structure as Claude Desktop.
- **Cline / Roo Code** — VS Code extension sidebar > MCP tab. Same JSON structure.
- **Zed** — Add to `settings.json` under `context_servers` key.

Each gets a brief config snippet or path. We don't need full walkthroughs — these tools' own docs cover the rest.

### Configuration

Intro: all options go in the `env` block of your MCP client config.

#### Providers (required)

Format: `PROVIDER_<NAME>="provider-name;api-key"`

At least one required. Supported providers:

| Variable | Example |
|----------|---------|
| `PROVIDER_OPENAI` | `openai;sk-your-key` |
| `PROVIDER_GEMINI` | `gemini;your-key` |
| `PROVIDER_OPENROUTER` | `openrouter;sk-or-your-key` |

Models are discovered dynamically from each provider's API — no need to list individual models.

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `CACHE_TTL_MINUTES` | `360` | How often to re-scan providers and re-fetch enrichment (minutes) |
| `ZERO_DATA_RETENTION` | `true` | Filter OpenRouter to ZDR-compatible models only |
| `LOG_LEVEL` | *(disabled)* | Enable file logging: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `~/.ask-another.log` | Log file path |
| `LOG_FILE_SIZE` | `5` | Max log file size in MB |
| `LOG_FILE_COUNT` | `2` | Number of rotation backups |
| `IMAGE_OUTPUT_DIR` | `~/Pictures/ask-another` | Where generated images are saved |
| `ANNOTATIONS_FILE` | `~/.ask-another-annotations.json` | Model metadata, usage, and notes |
| `FEEDBACK_LOG` | `~/.ask-another-feedback.jsonl` | Feedback log path |

## docs/reference.md

### Tools

Grouped by purpose. Each tool gets: name, one-line description, parameter list.

#### Discovery

| Tool | Description |
|------|-------------|
| `search_families` | Browse provider groupings (e.g. `openai`, `openrouter/deepseek`) |
| `search_models` | Find models with metadata — Elo, pricing, knowledge cutoff, notes |
| `refresh_models` | Force re-scan of providers and re-fetch enrichment data |

**search_families** params: `search` (optional substring), `zdr` (optional bool override)

**search_models** params: `search` (optional substring), `zdr` (optional bool override)

**refresh_models** params: none

#### Completion

| Tool | Description |
|------|-------------|
| `completion` | Query any model by full ID or favourite shorthand |

Params: `model` (required — full ID or shorthand), `prompt` (required), `system` (optional), `temperature` (optional, 0.0-2.0)

#### Research

| Tool | Description |
|------|-------------|
| `start_research` | Launch a background deep research task with web search and citations |
| `check_research` | List all research jobs, or retrieve results for a specific job |
| `cancel_research` | Cancel a running research task |

**start_research** params: `model` (required), `query` (required), `timeout` (optional, default 300s)

**check_research** params: `job_id` (optional — omit to list all)

**cancel_research** params: `job_id` (required)

#### Creative

| Tool | Description |
|------|-------------|
| `generate_image` | Generate images from text prompts, returned inline and saved to disk |

Params: `model` (required), `prompt` (required), `size` (optional), `quality` (optional)

#### Management

| Tool | Description |
|------|-------------|
| `annotate_models` | Add or update a personal note on a model |
| `feedback` | Report usability issues or suggestions |

**annotate_models** params: `model` (required — full ID), `note` (required)

**feedback** params: `issue` (required), `tool_name` (optional)

### Annotations & Enrichment

`~/.ask-another-annotations.json` is the single source of truth for model metadata, usage tracking, and personal notes.

#### What's stored

Each model entry has three optional sections:

- **metadata** — automatically populated: `arena_elo`, `knowledge_cutoff`, `organization`, `license`, `context_length`, `pricing_in`, `pricing_out`, `openrouter_listed`, `first_seen`, `last_updated`
- **usage** — tracked automatically: `call_count`, `last_used`
- **annotations** — user-set via `annotate_models`: `note`

#### Favourites

Favourites are the top 5 models by `call_count`. No configuration needed — just use the MCP and favourites emerge from actual usage. Favourites appear in the server instructions so the AI assistant knows your preferred models.

#### Enrichment sources

On startup (and on `refresh_models`), the server fetches:

1. **Elo ratings** from LMArena arena-catalog (GitHub JSON)
2. **Knowledge cutoff, organization, license** from LMArena metadata (HuggingFace CSV)
3. **Pricing, context length, listing date** from OpenRouter API

Enrichment is fail-safe — if any source errors, the server continues with partial data. Data refreshes automatically when `CACHE_TTL_MINUTES` expires.

### Architecture

- **Single file**: `src/ask_another/server.py` — the entire server
- **LiteLLM** — unified multi-provider LLM client
- **FastMCP** — MCP server framework
- **No database** — annotations JSON file + in-memory model cache
- **Dynamic discovery** — models fetched from provider APIs, no hardcoded list
- **Enrichment** — external metadata merged via normalized model name matching

### Development

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

#### Setup

```bash
git clone https://github.com/matthewgjohnson/ask-another
cd ask-another
uv sync
```

#### Running locally

```bash
PROVIDER_OPENAI="openai;sk-your-key" uv run ask-another
```

With debug logging:

```bash
LOG_LEVEL=DEBUG PROVIDER_OPENAI="openai;sk-your-key" uv run ask-another
```

#### Tests

Full suite (no API keys needed):

```bash
uv run --with pytest python -m pytest tests/ -v
```

Run individual test files:

```bash
uv run --with pytest python -m pytest tests/test_annotations.py -v
```

Test map:
- `test_annotations.py` — enrichment, normalisation, metadata, search
- `test_image_generation.py` — image generation paths
- `test_logging.py` — log config and rotation

#### Code layout

- `src/ask_another/server.py` — the entire server
- `tests/` — all tests, mocked (no network access needed)

#### Local state

The server persists state in `~/.ask-another-annotations.json`. If behaviour seems wrong during development, inspect or remove this file to reset.

#### No CI yet

Run the full test suite locally before opening a PR.

## Bonus Fix

`refresh_models` docstring (server.py line 827) still says "LiveBench and LMArena" — update to "LMArena arena-catalog and LMArena metadata" while we're touching docs.

## Not Changing

- `CLAUDE.md` — stays as the developer-facing project reference
- Server code (except the one docstring fix)
- Test files
- `pyproject.toml` (license already added)

## Files Changed

| File | Change |
|------|--------|
| `README.md` | Full rewrite — lean landing page |
| `docs/install.md` | New — uv install, client configs, config options |
| `docs/reference.md` | New — tools, annotations, architecture, development |
| `src/ask_another/server.py` | One-line docstring fix in `refresh_models` |
