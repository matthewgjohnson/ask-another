# ask-another v2-00

**Version**: v2-00
**Date**: 10 February 2026
**Type**: Specification

-----

## 1. Overview

ask-another is an MCP server that enables an MCP client (Claude, Gemini, etc.) to query other language models. It provides dynamic model discovery, a favourites system for convenient shorthand access, and a clean completion interface.

Version 2 introduces three architectural changes: provider configuration separates API keys from model selection, dynamic discovery replaces static model allowlists, and favourites enable shorthand access to preferred models.

-----

## 2. Tools

The server exposes two tools: one to discover available models and one to query them.

### 2.1 list_models

Returns available models from configured providers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | no | Filter results to a single provider (e.g. `openai`, `openrouter`) |
| `favourites_only` | bool | no | Return only models listed in `FAVOURITES`. Defaults to `false` |

The server queries each provider's model listing API on first invocation and caches the results in memory. Subsequent calls serve from cache until the TTL expires (default: 6 hours), at which point the next call triggers a refresh. The cache rebuilds on server restart.

Returns an array of model identifiers in `provider/model-name` format.

### 2.2 completion

Sends a prompt to the specified model and returns the response.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | yes | Full model identifier or favourite shorthand |
| `prompt` | string | yes | The question or prompt to send |
| `system` | string | no | Optional system prompt |
| `temperature` | float | no | 0.0-2.0, defaults to 1.0 |

Model resolution follows two steps:

1. Full identifier (e.g. `openai/gpt-4o`) routes directly
2. Shorthand (e.g. `openai`) matches against favourites by provider prefix, resolving to the full identifier

Unresolvable shorthand returns an error listing available favourites.

Returns the text response from the model, or an error message.

-----

## 3. Model Identifiers

Models use the format `provider/model-name`. Each provider's API returns identifiers in this format natively through LiteLLM, with normalisation applied where needed (see section 6.1).

| Provider | Examples |
|----------|----------|
| OpenAI | `openai/gpt-4o`, `openai/gpt-4o-mini` |
| Google | `gemini/gemini-2.5-pro-preview-05-06`, `gemini/gemini-2.0-flash` |
| OpenRouter | `openrouter/openai/gpt-4o`, `openrouter/anthropic/claude-3.5-sonnet` |

OpenRouter identifiers include the original provider as a path segment, making them naturally distinct from direct provider identifiers.

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
        "FAVOURITES": "openai/gpt-4o,gemini/gemini-2.5-pro-preview-05-06,openrouter/anthropic/claude-3.5-sonnet",
        "CACHE_TTL": "360"
      }
    }
  }
}
```

### 4.1 Providers

Each `PROVIDER_*` variable defines one provider connection. Format: `provider-name;api-key`. The server scans for all environment variables matching the `PROVIDER_*` pattern on startup. The variable suffix is descriptive (e.g. `PROVIDER_OPENAI`, `PROVIDER_GEMINI`) and carries no semantic meaning.

### 4.2 Favourites

The `FAVOURITES` variable defines a comma-separated list of preferred model identifiers. Favourites serve two purposes: filtering `list_models` results when `favourites_only` is true, and enabling shorthand resolution in `completion` calls.

Shorthand resolution extracts the provider prefix from each favourite. When `completion` receives `openai` as the model, it matches the favourite starting with `openai/` and resolves to `openai/gpt-4o`. One favourite per provider prefix is permitted to keep resolution unambiguous.

### 4.3 Cache TTL

The `CACHE_TTL` variable sets the model list cache duration in minutes. Defaults to 360 (6 hours) if omitted. The cache is in-memory only and rebuilds on server restart.

-----

## 5. Error Handling

The server handles errors as follows.

| Condition | Behaviour |
|-----------|-----------|
| Invalid PROVIDER_* format | Error on startup, names the malformed variable |
| Provider API unreachable | Warn and exclude provider from cache, serve remaining providers |
| Model not found | Error: "Model not found. Use list_models to see available models" |
| Unresolvable shorthand | Error: "No favourite matches '[shorthand]'. Available favourites: [list]" |
| Duplicate provider prefix in FAVOURITES | Error on startup: "Multiple favourites for provider '[prefix]'" |
| Rate limit | Pass through provider's error |
| Timeout | 60 second default, return timeout error |

-----

## 6. Implementation Notes

The reference implementation uses Python with uv as package manager and LiteLLM as the unified LLM interface. LiteLLM provides a single `completion()` call that routes to 100+ providers, handling authentication and response normalisation.

### 6.1 Model Discovery

Model discovery uses LiteLLM as the default mechanism and falls back to direct API calls for providers where LiteLLM support is incomplete.

**Default path.** The server calls `litellm.get_valid_models(check_provider_endpoint=True, custom_llm_provider=provider, api_key=key)` for each configured provider. This queries the provider's model listing API and returns available model identifiers.

**ID normalisation.** LiteLLM returns identifiers in inconsistent formats across providers. Some include the provider prefix (e.g. `gemini/gemini-2.0-flash`), others omit it (e.g. `gpt-4o` from OpenAI). The server applies a generic normalisation rule: if an identifier does not start with `{provider}/`, the server prepends it. This is a single rule that works for all providers without per-provider logic.

**Exception handlers.** Providers where `get_valid_models` does not support live API queries are handled through a registry of exception functions. Each exception function makes a direct API call and returns normalised identifiers. OpenRouter is the known exception at time of writing -- its listing endpoint (`GET https://openrouter.ai/api/v1/models`) is public and returns identifiers in `provider/model` format, which the server prepends with `openrouter/`.

### 6.2 Caching

Results are cached in a dictionary keyed by provider name, with a timestamp for TTL expiry. On cache miss or expiry, the server fetches fresh results for that provider only.

-----

## 7. Future Considerations

The following features are not included in v2: conversation history and multi-turn support, streaming responses, token counting and cost tracking, image generation via compatible providers, and provider-specific tools such as Grok search and Gemini grounding.

-----

*End of document*
