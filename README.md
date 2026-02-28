# ask-another

An MCP server that lets Claude Desktop (or any MCP client) query other LLMs through a unified interface. Dynamic model discovery, favourites for shorthand access, and tiered search across hundreds of models.

## Installation (macOS)

### Prerequisites

Install [uv](https://docs.astral.sh/uv/) if you haven't already:

```bash
brew install uv
```

### Claude Desktop Setup

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ask-another": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
      "env": {
        "PROVIDER_OPENAI": "openai;sk-your-openai-key",
        "PROVIDER_GEMINI": "gemini;your-google-key",
        "PROVIDER_OPENROUTER": "openrouter;sk-or-your-openrouter-key",
        "FAVOURITES": "openai/gpt-5.2-pro,gemini/gemini-3-pro-preview,openrouter/anthropic/claude-sonnet-4-20250514",
        "CACHE_TTL": "360"
      }
    }
  }
}
```

That's it! Claude Desktop will automatically fetch and run the server.

## Configuration

### Providers

Configure providers via `PROVIDER_*` environment variables. Format: `provider-name;api-key`

```
PROVIDER_OPENAI="openai;sk-your-openai-key"
PROVIDER_GEMINI="gemini;your-google-key"
PROVIDER_OPENROUTER="openrouter;sk-or-your-openrouter-key"
```

Models are discovered dynamically from each provider's API -- no need to list individual models.

### Favourites

The `FAVOURITES` variable defines preferred models for shorthand access. One favourite per family (e.g. `openai`, `openrouter/deepseek`).

```
FAVOURITES="openai/gpt-5.2-pro,gemini/gemini-3-pro-preview,openrouter/deepseek/deepseek-r1-0528"
```

With this config, passing `openai` to completion resolves to `openai/gpt-5.2-pro`. For OpenRouter, use the family prefix: `openrouter/deepseek` resolves to `openrouter/deepseek/deepseek-r1-0528`.

### Zero Data Retention

ZDR filtering is **on by default** — OpenRouter model discovery only returns models that support zero data retention. Set `ZERO_DATA_RETENTION` to `false` to disable this and list all models.

### Cache TTL

`CACHE_TTL` sets model list cache duration in minutes. Defaults to 360 (6 hours).

## Tools

### search_families

Browse available provider groupings.

- `search` (optional): Substring filter on family names

### search_models

Search for specific model identifiers. Results include descriptions from the model catalog when available.

- `search` (optional): Substring filter on model identifiers

### completion

Query a specified LLM.

- `model` (required): Full identifier (e.g. `openai/gpt-5.2-pro`) or favourite shorthand (e.g. `openai`)
- `prompt` (required): The user prompt
- `system` (optional): System prompt
- `temperature` (optional): 0.0-2.0, default 1.0

### feedback

Report usability issues with the MCP server. The LLM client is instructed to call this whenever a tool call fails, returns confusing output, or it's unsure how to proceed. Entries are appended to a JSONL log file for the developer to review and improve the server.

- `issue` (required): Description of what went wrong
- `tool_name` (optional): Which tool was involved

Log location defaults to `~/.ask-another-feedback.jsonl`, configurable via `FEEDBACK_LOG` env var.

## Development

```bash
git clone https://github.com/matthewgjohnson/ask-another
cd ask-another
uv sync
PROVIDER_OPENAI="openai;sk-test" uv run ask-another
```
