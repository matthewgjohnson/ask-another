# ask-another v1-03

**Version**: v1-03
**Date**: 04 February 2026
**Type**: Specification

-----

## 1. Overview

ask-another is an MCP server that supports queries to other LLMs.

It enables an MCP client (Claude, Gemini, etc.) to query other language models. Clean interface, explicit model allowlist, no provider-specific features in v1.

-----

## 2. Tools

The server exposes two tools: one to discover available models and one to query them.

### 2.1 list_models

Returns the list of available models based on the `MODEL_*` configuration.

This tool takes no parameters and returns an array of model identifiers.

### 2.2 completion

Sends a prompt to the specified model and returns the response.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | yes | Model identifier in `provider/model` format |
| `prompt` | string | yes | The question or prompt to send |
| `system` | string | no | Optional system prompt |
| `temperature` | float | no | 0.0-2.0, defaults to 1.0 |

Returns the text response from the model, or an error message.

-----

## 3. Model Identifiers

Models use the format `provider/model-name`.

| Provider | Examples |
|----------|----------|
| OpenAI | `openai/gpt-4o`, `openai/gpt-4o-mini` |
| Google | `gemini/gemini-pro`, `gemini/gemini-1.5-pro` |
| xAI | `xai/grok-beta` |
| Anthropic | `anthropic/claude-3-5-sonnet-20241022` |
| Meta (via Groq) | `groq/llama-3.1-70b-versatile` |

-----

## 4. Configuration

All configuration uses environment variables in Claude Desktop config.

```json
{
  "mcpServers": {
    "ask-another": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
      "env": {
        "MODEL_GPT4": "openai/gpt-4o;sk-...",
        "MODEL_GEMINI": "gemini/gemini-pro;AIza...",
        "MODEL_GROK": "xai/grok-beta;xai-..."
      }
    }
  }
}
```

Each `MODEL_*` variable defines one allowed model. Format: `provider/model-name;api-key`. The server scans for all environment variables matching the `MODEL_*` pattern on startup. Use descriptive names for the variable suffix (e.g., `MODEL_GPT4`, `MODEL_GEMINI`) rather than numbers.

-----

## 5. Error Handling

The server handles errors as follows.

| Condition | Behaviour |
|-----------|-----------|
| Model not in allowlist | Error: "Model not allowed" |
| Invalid MODEL_* format | Error on startup, names the malformed variable |
| Rate limit | Pass through provider's error |
| Invalid model | Pass through error |
| Timeout | 60 second default, return timeout error |

-----

## 6. Implementation Notes

The reference implementation uses Python with uv as package manager and LiteLLM as the unified LLM interface. LiteLLM provides a single `completion()` call that routes to 100+ providers, handling authentication and response normalisation. This avoids managing separate SDKs per provider.

-----

## 7. Future Considerations

The following features are not included in v1: conversation history and multi-turn support, streaming responses, token counting and cost tracking, and provider-specific tools such as Grok search and Gemini grounding.

-----

*End of document*
