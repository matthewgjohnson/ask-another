# ask-another

An MCP server that enables querying other LLMs (OpenAI, Gemini, xAI, Anthropic, Groq) through a unified interface.

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
        "MODEL_GPT4": "openai/gpt-4o;sk-your-openai-key",
        "MODEL_GEMINI": "gemini/gemini-pro;your-google-key"
      }
    }
  }
}
```

That's it! Claude Desktop will automatically fetch and run the server.

## Configuration

Configure models via environment variables with the `MODEL_*` prefix in the `env` section above.

**Format:** `provider/model-name;api-key`

Examples:
```
MODEL_GPT4="openai/gpt-4o;sk-your-openai-key"
MODEL_GEMINI="gemini/gemini-pro;your-google-key"
MODEL_CLAUDE="anthropic/claude-3-5-sonnet-20241022;sk-ant-your-key"
MODEL_GROK="xai/grok-beta;xai-your-key"
MODEL_LLAMA="groq/llama-3.1-70b-versatile;gsk-your-groq-key"
```

## Tools

### list_models

Lists all configured model identifiers.

**Returns:** Array of model identifiers (e.g., `["openai/gpt-4o", "gemini/gemini-pro"]`)

### completion

Get a completion from a specified LLM.

**Parameters:**
- `model` (required): Model identifier in `provider/model-name` format
- `prompt` (required): The user prompt
- `system` (optional): System prompt
- `temperature` (optional): 0.0-2.0, default 1.0

**Returns:** The model's text response

## Supported Providers

Via LiteLLM, supports:
- OpenAI (`openai/gpt-4o`, `openai/gpt-4o-mini`, etc.)
- Anthropic (`anthropic/claude-3-5-sonnet-20241022`, etc.)
- Google (`gemini/gemini-pro`, `gemini/gemini-1.5-pro`, etc.)
- xAI (`xai/grok-beta`, etc.)
- Groq (`groq/llama-3.1-70b-versatile`, etc.)

See [LiteLLM providers](https://docs.litellm.ai/docs/providers) for full list.

## Development

```bash
git clone https://github.com/matthewgjohnson/ask-another
cd ask-another
uv sync
MODEL_TEST="openai/gpt-4o-mini;sk-test" uv run ask-another
```
