# Reference

## Tools

### Discovery

| Tool | Description |
|------|-------------|
| `search_families` | Browse provider groupings (e.g. `openai`, `openrouter/deepseek`) |
| `search_models` | Find models with metadata — Elo, pricing, knowledge cutoff, notes |
| `refresh_models` | Force re-scan of providers and re-fetch enrichment data |

**search_families**
- `search` *(optional)* — substring filter on family names
- `zdr` *(optional)* — override ZDR filtering (bool)

**search_models**
- `search` *(optional)* — substring filter on model identifiers
- `zdr` *(optional)* — override ZDR filtering (bool)

**refresh_models** — no parameters

### Completion

| Tool | Description |
|------|-------------|
| `completion` | Query any model by full ID or favourite shorthand |

- `model` *(required)* — full model identifier (e.g. `openai/gpt-5.2`) or favourite shorthand (e.g. `openai`)
- `prompt` *(required)* — the user prompt
- `system` *(optional)* — system prompt
- `temperature` *(optional)* — 0.0-2.0, omit to use model default

Shorthand resolves to the most-used model in that family. For example, if you use `openai/gpt-5.2` most often, passing `openai` will route to it.

### Research

| Tool | Description |
|------|-------------|
| `start_research` | Launch a background deep research task with web search and citations |
| `check_research` | List all research jobs, or retrieve results for a specific job |
| `cancel_research` | Cancel a running research task |

**start_research**
- `model` *(required)* — e.g. `openrouter/perplexity/sonar-deep-research`
- `query` *(required)* — the research question
- `timeout` *(optional)* — max seconds to wait (default 300)

**check_research**
- `job_id` *(optional)* — specific job to retrieve. Omit to list all jobs.

**cancel_research**
- `job_id` *(required)* — job to cancel

### Creative

| Tool | Description |
|------|-------------|
| `generate_image` | Generate images from text prompts, returned inline and saved to disk |

- `model` *(required)* — e.g. `openai/gpt-image-1`, `gemini/gemini-2.5-flash-image`
- `prompt` *(required)* — text description of the image
- `size` *(optional)* — e.g. `1024x1024`, `1536x1024` (dedicated image models only)
- `quality` *(optional)* — `low`, `medium`, `high`, `hd`, `standard` (dedicated image models only)

### Management

| Tool | Description |
|------|-------------|
| `annotate_models` | Add or update a personal note on a model |
| `feedback` | Report usability issues or suggestions |

**annotate_models**
- `model` *(required)* — full model identifier
- `note` *(required)* — your note (overwrites any existing note)

**feedback**
- `issue` *(required)* — what went wrong or what could be better
- `tool_name` *(optional)* — which tool was involved

## Annotations & Enrichment

`~/.ask-another-annotations.json` is the single source of truth for model metadata, usage tracking, and personal notes.

### What's stored

Each model entry has three optional sections:

- **metadata** — automatically populated on startup:
  `arena_elo`, `knowledge_cutoff`, `organization`, `license`, `context_length`, `pricing_in`, `pricing_out`, `openrouter_listed`, `first_seen`, `last_updated`
- **usage** — tracked automatically on each `completion` call:
  `call_count`, `last_used`
- **annotations** — set by you via `annotate_models`:
  `note`

### Favourites

The top 5 models by `call_count` become your favourites. No configuration needed — just use the MCP and favourites emerge from actual usage. Favourites appear in the server instructions so your AI assistant knows your preferred models.

### Enrichment sources

On startup (and when you call `refresh_models`), the server fetches:

1. **Elo ratings** — from [LMArena arena-catalog](https://github.com/lmarena/arena-catalog) (GitHub JSON)
2. **Knowledge cutoff, organization, license** — from LMArena metadata (HuggingFace CSV)
3. **Pricing, context length, listing date** — from the OpenRouter API

Enrichment is fail-safe: if any source errors, the server continues with partial data. Data refreshes automatically when `CACHE_TTL_MINUTES` expires.

## Architecture

- **Single file** — `src/ask_another/server.py` is the entire server
- **[LiteLLM](https://github.com/BerriAI/litellm)** — unified multi-provider LLM client
- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP server framework
- **No database** — annotations JSON file + in-memory model cache
- **Dynamic discovery** — models fetched from provider APIs, no hardcoded model list
- **Name matching** — arena metadata is matched to provider models via normalized model names (strip provider prefix, dates, common suffixes)

## Development

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

### Setup

```bash
git clone https://github.com/matthewgjohnson/ask-another
cd ask-another
uv sync
```

### Running locally

```bash
PROVIDER_OPENAI="openai;sk-your-key" uv run ask-another
```

With debug logging:

```bash
LOG_LEVEL=DEBUG PROVIDER_OPENAI="openai;sk-your-key" uv run ask-another
```

Provider credentials are required for manual testing of provider-backed tools, but all tests run without API keys.

### Tests

Full suite:

```bash
uv run --with pytest python -m pytest tests/ -v
```

Individual test files:

```bash
uv run --with pytest python -m pytest tests/test_annotations.py -v
```

Test map:
- `test_annotations.py` — enrichment, normalisation, metadata, search
- `test_feedback.py` — feedback tool and JSONL logging
- `test_image_generation.py` — image generation paths
- `test_logging.py` — log config and rotation

### Code layout

- `src/ask_another/server.py` — the entire server
- `tests/` — all tests, mocked (no network access needed)

### Local state

The server persists state in `~/.ask-another-annotations.json`. If behaviour seems wrong during development, inspect or remove this file to reset.

### No CI yet

Please run the full test suite locally before opening a PR.
