# README Rewrite Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the outdated README with a lean landing page and two linked docs (install guide + reference).

**Architecture:** Hub-and-spoke — README.md is a ~60-line quick start, linking to docs/install.md (setup + config) and docs/reference.md (tools + annotations + dev guide). Two stale docstrings in server.py are fixed as a side-effect.

**Tech Stack:** Markdown, one Python docstring edit

**Spec:** `docs/superpowers/specs/2026-03-13-readme-rewrite-design.md`

---

## Chunk 1: README.md rewrite + docstring fixes

### Task 1: Rewrite README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README.md contents**

```markdown
# ask-another

An MCP server that gives your AI assistant access to other LLMs. Query hundreds of models across OpenAI, Google, and OpenRouter through a single interface — with model discovery, usage-based favourites, and automatic enrichment (Elo ratings, pricing, knowledge cutoffs).

## Quick Start

1. Install [uv](https://docs.astral.sh/uv/) (see [Installation Guide](docs/install.md) for Linux/Windows):

```bash
brew install uv
```

2. Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

At least one provider is required. Remove any you don't have keys for.

3. Restart Claude Desktop.

## What You Can Do

- "Ask GPT-5.2 what it thinks about this architecture" → `completion`
- "What Gemini models are available?" → `search_models`
- "Research the state of WebAssembly in 2026" → `start_research`
- "Generate a logo for my project" → `generate_image`
- "Note that DeepSeek is good for creative writing" → `annotate_models`

See all 10 tools in the [Reference](docs/reference.md).

## Learn More

- **[Installation Guide](docs/install.md)** — Linux/Windows setup, Claude Code, Cursor, Windsurf, and other MCP clients, all configuration options
- **[Reference](docs/reference.md)** — tools, annotations & enrichment, architecture, development

## License

[MIT](LICENSE)
```

- [ ] **Step 2: Verify the markdown renders correctly**

Run: `cat README.md | head -60`
Check: headings, code blocks, links look correct

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README as lean landing page with links to detail docs"
```

### Task 2: Fix stale docstrings in server.py

**Files:**
- Modify: `src/ask_another/server.py:827` (refresh_models docstring)
- Modify: `src/ask_another/server.py:949` (generate_image docstring)

- [ ] **Step 1: Fix refresh_models docstring**

In `src/ask_another/server.py`, find the `refresh_models` docstring (around line 827):

```python
# Old:
"""Force a re-scan of all configured providers and re-fetch benchmark
data from LiveBench and LMArena. Use this if model data seems stale
or after adding a new provider.
"""

# New:
"""Force a re-scan of all configured providers and re-fetch enrichment
data from LMArena arena-catalog and LMArena metadata. Use this if
model data seems stale or after adding a new provider.
"""
```

- [ ] **Step 2: Fix generate_image docstring**

In `src/ask_another/server.py`, find the `generate_image` docstring (around line 949):

```python
# Old:
and saved to disk (~/.Pictures/ask-another/ by default).

# New:
and saved to disk (~/Pictures/ask-another by default).
```

- [ ] **Step 3: Run tests to make sure nothing broke**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add src/ask_another/server.py
git commit -m "fix: correct stale docstrings in refresh_models and generate_image"
```

---

## Chunk 2: docs/install.md

### Task 3: Create docs/install.md

**Files:**
- Create: `docs/install.md`

- [ ] **Step 1: Write docs/install.md**

```markdown
# Installation

## Install uv

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. Install it with your platform's package manager:

| Platform | Command |
|----------|---------|
| macOS | `brew install uv` |
| Arch Linux | `pacman -S uv` |
| Fedora | `dnf install uv` |
| Windows | `winget install astral-sh.uv` |

`uv` is not in the default Debian/Ubuntu apt repos. For Ubuntu, use `snap install uv` or `brew install uv` ([Homebrew on Linux](https://brew.sh/)). See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for all options.

## Client Setup

### Claude Desktop

Config file location:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add the following to your config file:

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

At least one provider is required. Remove any you don't have keys for.

Restart Claude Desktop after saving.

### Claude Code

```bash
claude mcp add ask-another \
  -e PROVIDER_OPENAI="openai;sk-your-key" \
  -e PROVIDER_GEMINI="gemini;your-key" \
  -e PROVIDER_OPENROUTER="openrouter;sk-or-your-key" \
  -- uvx --from git+https://github.com/matthewgjohnson/ask-another ask-another
```

### Other Clients

<details>
<summary>Cursor</summary>

Go to **Settings > Features > MCP > Add New MCP Server**. Set:
- **Command:** `uvx`
- **Args:** `--from git+https://github.com/matthewgjohnson/ask-another ask-another`

Add provider environment variables in the server's env section.

See [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol) for details.
</details>

<details>
<summary>Windsurf</summary>

Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "ask-another": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
      "env": {
        "PROVIDER_OPENAI": "openai;sk-your-key"
      }
    }
  }
}
```
</details>

<details>
<summary>Cline / Roo Code (VS Code)</summary>

Open the MCP tab in the extension sidebar and add a server with the same JSON structure as the Claude Desktop config above.
</details>

<details>
<summary>Zed</summary>

Add to your Zed `settings.json` under `context_servers`:

```json
{
  "context_servers": {
    "ask-another": {
      "command": {
        "path": "uvx",
        "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
        "env": {
          "PROVIDER_OPENAI": "openai;sk-your-key"
        }
      }
    }
  }
}
```
</details>

## Configuration

All options go in the `env` block of your MCP client config.

### Providers

Format: `PROVIDER_<NAME>="provider-name;api-key"`

At least one provider is required. Models are discovered dynamically from each provider's API — no need to list individual models.

| Variable | Example |
|----------|---------|
| `PROVIDER_OPENAI` | `openai;sk-your-key` |
| `PROVIDER_GEMINI` | `gemini;your-key` |
| `PROVIDER_OPENROUTER` | `openrouter;sk-or-your-key` |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `CACHE_TTL_MINUTES` | `360` | How often to re-scan providers and re-fetch enrichment (minutes) |
| `ZERO_DATA_RETENTION` | enabled | Filter OpenRouter to ZDR-compatible models only. Set to `false` to disable |
| `LOG_LEVEL` | *(disabled)* | Enable file logging: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `~/.ask-another.log` | Log file path |
| `LOG_FILE_SIZE` | `5` | Max log file size in MB |
| `LOG_FILE_COUNT` | `2` | Number of rotation backups |
| `IMAGE_OUTPUT_DIR` | `~/Pictures/ask-another` | Where generated images are saved |
| `ANNOTATIONS_FILE` | `~/.ask-another-annotations.json` | Model metadata, usage, and notes |
| `FEEDBACK_LOG` | `~/.ask-another-feedback.jsonl` | Feedback log path |
```

- [ ] **Step 2: Verify the markdown renders correctly**

Run: `cat docs/install.md | wc -l`
Expected: ~130-160 lines

- [ ] **Step 3: Commit**

```bash
git add docs/install.md
git commit -m "docs: add installation guide with multi-platform and multi-client setup"
```

---

## Chunk 3: docs/reference.md

### Task 4: Create docs/reference.md

**Files:**
- Create: `docs/reference.md`

- [ ] **Step 1: Write docs/reference.md**

```markdown
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
```

- [ ] **Step 2: Verify line count and structure**

Run: `cat docs/reference.md | wc -l`
Expected: ~200-240 lines

- [ ] **Step 3: Commit**

```bash
git add docs/reference.md
git commit -m "docs: add reference guide with tools, annotations, architecture, and dev setup"
```

---

## Chunk 4: Final verification

### Task 5: Verify all links and push

- [ ] **Step 1: Check all cross-references**

Verify these links resolve to real files:
- `README.md` links to `docs/install.md` and `docs/reference.md`
- `README.md` links to `LICENSE`

Run: `ls README.md LICENSE docs/install.md docs/reference.md`
Expected: all four files listed

- [ ] **Step 2: Run full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: all tests pass (docstring changes don't affect tests)

- [ ] **Step 3: Push**

```bash
git push
```
