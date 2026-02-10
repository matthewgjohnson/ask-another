# ask-another v2-03

**Version**: v2-03
**Date**: 10 February 2026
**Type**: Specification

-----

## 1. Overview

ask-another is an MCP server that enables an MCP client (Claude, Gemini, etc.) to query other language models. It provides tiered model discovery, a favourites system for convenient shorthand access, and a clean completion interface.

Version 2 introduces three architectural changes: provider configuration separates API keys from model selection, dynamic discovery replaces static model allowlists, and a two-tier search (families and models) enables practical discovery across hundreds of models.

-----

## 2. Tools

The server exposes three tools: two for discovery and one for querying models.

### 2.1 search_families

Returns model families available across configured providers. Families are the natural groupings within model identifiers -- `openai`, `openrouter/openai`, `openrouter/anthropic`, `gemini`, and so on.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search` | string | no | Substring filter applied to family names |
| `favourites_only` | bool | no | Return only families containing favourite models. Defaults to `false` |

Returns matching families as a newline-separated list. This is the recommended first discovery call, providing a compact overview without flooding context with hundreds of model identifiers.

### 2.2 search_models

Returns specific model identifiers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search` | string | no | Substring filter applied to full model identifiers |
| `favourites_only` | bool | no | Return only favourite models. Defaults to `false` |

Returns matching model identifiers as a newline-separated list.

### 2.3 completion

Sends a prompt to the specified model and returns the response.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | yes | Full model identifier or favourite shorthand |
| `prompt` | string | yes | The question or prompt to send |
| `system` | string | no | Optional system prompt |
| `temperature` | float | no | 0.0-2.0, defaults to 1.0 |

Model resolution follows two steps:

1. Full identifier (e.g. `openai/gpt-5.2-pro`) routes directly
2. Shorthand (e.g. `openai`) matches against favourites by provider prefix, resolving to the full identifier

Unresolvable shorthand returns an error listing available favourites.

Returns the text response from the model, or an error message.

-----

## 3. Model Identifiers

Full model identifiers use the format `provider/model-name`, following LiteLLM conventions.

| Provider | Examples |
|----------|----------|
| OpenAI | `openai/gpt-5.2-pro`, `openai/gpt-4o` |
| Google | `gemini/gemini-3-pro-preview`, `gemini/gemini-2.5-flash` |
| xAI | `xai/grok-2`, `xai/grok-2-mini` |
| OpenRouter | `openrouter/openai/gpt-5-pro`, `openrouter/anthropic/claude-opus-4.5` |

OpenRouter identifiers include the original provider as a path segment, making them naturally distinct from direct provider identifiers.

Families derive naturally from identifier prefixes: a family is all path segments except the last. For direct providers, the family is the provider itself (`openai`, `gemini`). For OpenRouter, the family includes the organisation segment (`openrouter/openai`, `openrouter/anthropic`).

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
        "PROVIDER_OPENAI": "openai;sk-...",
        "PROVIDER_OPENROUTER": "openrouter;or-...",
        "PROVIDER_GEMINI": "gemini;AIza...",
        "PROVIDER_XAI": "xai;xai-...",
        "FAVOURITES": "openai/gpt-5.2-pro,gemini/gemini-3-pro-preview,xai/grok-2",
        "CACHE_TTL": "360"
      }
    }
  }
}
```

### 4.1 Providers

Each `PROVIDER_*` variable defines one provider connection. Format: `provider-name;api-key`. The server scans for all environment variables matching the `PROVIDER_*` pattern on startup. The variable suffix is descriptive (e.g. `PROVIDER_OPENAI`, `PROVIDER_GEMINI`) and carries no semantic meaning.

### 4.2 Favourites

The `FAVOURITES` variable defines a comma-separated list of preferred model identifiers. Favourites enable shorthand resolution in `completion` calls and filtering in discovery tools.

Shorthand resolution extracts the provider prefix from each favourite. When `completion` receives `openai` as the model, it matches the favourite starting with `openai/` and resolves to the full identifier. One favourite per provider prefix is permitted to keep resolution unambiguous.

### 4.3 Cache

The server queries each provider's model listing API on first discovery call and caches the results in memory. Subsequent calls serve from cache until the TTL expires, at which point the next call triggers a refresh. The cache rebuilds on server restart.

The `CACHE_TTL` variable sets the cache duration in minutes. Defaults to 360 (6 hours) if omitted.

-----

## 5. Error Handling

The server handles errors as follows.

| Condition | Behaviour |
|-----------|-----------|
| Invalid PROVIDER_* format | Error on startup, names the malformed variable |
| Provider API unreachable | Warn and exclude provider from cache, serve remaining providers |
| Model not found | Error: "Model not found. Use search_models to find available models" |
| Unresolvable shorthand | Error: "No favourite matches '[shorthand]'. Available favourites: [list]" |
| Duplicate provider prefix in FAVOURITES | Error on startup: "Multiple favourites for provider '[prefix]'" |
| Rate limit | Pass through provider's error |
| Timeout | 60 second default, return timeout error |

-----

## 6. Implementation Notes

The reference implementation uses Python with uv as package manager and LiteLLM as the unified LLM interface. LiteLLM provides a single `completion()` call that routes to 100+ providers, handling authentication and response normalisation.

### 6.1 Model Discovery

Dynamic model discovery uses `get_valid_models(check_provider_endpoint=True)` as the default listing mechanism. Results are cached in a dictionary keyed by provider name with a timestamp for TTL expiry. Empty results are excluded from the cache to prevent provider outages from overwriting previously valid data.

### 6.2 ID Normalisation

Model identifiers from provider APIs may omit the provider prefix. The server applies a generic normalisation rule: prepend `provider/` if the identifier does not already include it.

### 6.3 Provider-Specific Handling

Providers with non-standard listing APIs use an exception handler registry. OpenRouter requires custom handling due to its different endpoint structure and response format.

-----

## 7. Future Considerations

The following features are not included in v2: conversation history and multi-turn support, streaming responses, token counting and cost tracking, model metadata in search results (context window, pricing), image generation via compatible providers, and provider-specific tools such as Grok search and Gemini grounding.

-----

*End of document*
