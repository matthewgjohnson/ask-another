# Provider Status Block

**Date:** 2026-05-27
**Status:** Draft
**Addresses:** Silent loss of sensitive plugin `user_config` (e.g., API keys cleared by Claude Code auto-update) leaves providers invisibly unavailable; the assistant only discovers the loss when a tool call fails.

## Problem

Sensitive plugin `user_config` values are stored in the macOS Keychain and substituted at MCP-subprocess-spawn time via `${user_config.provider_*}`. Known Claude Code auto-update bugs ([#17490](https://github.com/anthropics/claude-code/issues/17490), [#40714](https://github.com/anthropics/claude-code/issues/40714)) can clear individual values without warning. After commit `5eff401` (skip empty `PROVIDER_*` env vars instead of crashing), this loss is silent at server startup — the affected provider simply does not appear in `_provider_registry`.

The existing `Unavailable Providers:` section (introduced by the provider-health-validation spec, 2026-03-29) only surfaces providers that errored *after* being configured and used. It does not surface providers that were declared in the plugin manifest but are *missing from the runtime environment*.

Result: the assistant has no way to know at session start which expected providers are configured. Loss is discovered only when a tool call fails — exactly the scenario that prompted this design.

## Design

### Source of truth: the plugin manifest

The expected set of providers is derived from the plugin manifest at startup. The plugin spec's `user_config` schema is constrained to a flat list of named scalar fields (no arrays, no conditionals — see [plugins-reference](https://code.claude.com/docs/en/plugins-reference)), so the manifest is the only declarative file that already enumerates which providers the plugin supports. Duplicating that list in `server.py` would create lockstep editing across two files for every provider added.

### Manifest discovery

A new helper `_discover_expected_providers() -> tuple[str, ...]` walks up from `server.py`'s `__file__` looking for either:

- `manifest.json` at any ancestor directory (MCPB bundle layout — combines schema + env wiring in one file), OR
- `.claude-plugin/plugin.json` at any ancestor directory (Claude Code plugin layout — schema and env wiring split across `plugin.json` + `.mcp.json`)

First match wins. Both formats use `user_config` (snake_case) at the top level. The helper:

1. Parses the JSON
2. Extracts all keys under `user_config` matching the regex `^provider_(.+)$`
3. Strips the `provider_` prefix
4. Returns the resulting tuple in declaration order (Python dict iteration order = manifest insertion order)

If no manifest is reachable within a bounded number of ancestor levels (cap at 5), the helper returns an empty tuple.

Manifest-parse failures (malformed JSON, missing `user_config` key, etc.) are logged at WARNING level and treated as "no manifest found" — the section is omitted rather than crashing the server.

### Status derivation

For each expected provider, status is determined by membership in `_provider_registry`:

- In registry → `configured`
- Not in registry → `not configured`

Both status values are plain strings. This leaves room for future enrichment (e.g., `configured (auth failed)`) if active probing is added later, without restructuring the format.

### Surfacing in `_build_instructions()`

A new section is appended to the instructions string, positioned between the existing `Purpose:` and `Howto:` blocks:

```
Providers:
  - openai: configured
  - gemini: configured
  - openrouter: not configured
```

The section is included when `_discover_expected_providers()` returns a non-empty tuple. It is omitted entirely when the tuple is empty (local-dev mode with no manifest reachable).

Rationale for placement above `Howto:`: provider status determines what the assistant can do at all. Surfacing it before the usage instructions is more useful than burying it below the model lists. It is intentionally below `Purpose:` so the first thing the reader sees is still what the server is for.

### Interaction with existing `Unavailable Providers:` section

Kept as-is. The two sections convey distinct information:

| Section | Source | Meaning |
|---|---|---|
| `Providers:` (new) | env var presence at startup | "Was this provider's key supplied?" |
| `Unavailable Providers:` (existing) | runtime model-discovery errors | "Did this provider's key work when we tried it?" |

Both can appear in the same instructions string without redundancy. A provider listed as `configured` in the new section may also appear in `Unavailable Providers:` if its key is invalid and discovery fails — the two together give the assistant a complete picture.

## Scope

### In scope

- `_discover_expected_providers()` helper in `server.py` with manifest walk-up logic (handles MCPB and Claude Code plugin layouts)
- New `Providers:` section in `_build_instructions()` between `Purpose:` and `Howto:`
- Tests in `tests/test_provider_config.py` covering both manifest layouts, malformed-manifest handling, and local-dev fallback

### Out of scope

- Active auth probing — explicitly deferred; user preference is the cheap env-var check until/unless the loss pattern repeats with valid-but-broken keys
- Restructuring or removing the existing `Unavailable Providers:` section
- Caching the discovery result beyond what happens naturally (it runs once during module import when `_build_instructions()` is called from the `FastMCP()` constructor)
- Reading the manifest's `description` or `title` fields to produce richer per-provider labels
- Surfacing the same status anywhere other than the opening instructions (e.g., as a separate MCP tool or skill — the existing `ask-another:status` skill is unchanged)

## Testing

Extend `tests/test_provider_config.py` with the following cases:

- `_discover_expected_providers()` finds and parses an MCPB-style `manifest.json` placed in a fixture directory above a stub `server.py`, returning the expected `provider_*` keys
- Same for a Claude Code plugin-style `.claude-plugin/plugin.json`
- Returns `()` when no manifest is reachable within the walk-up cap
- Returns `()` and logs a warning when the manifest exists but is malformed JSON or missing `user_config`
- `_build_instructions()` includes a `Providers:` section when the expected set is non-empty, with each entry showing the correct `configured` / `not configured` status based on `_provider_registry`
- `_build_instructions()` omits the section entirely when `_discover_expected_providers()` returns `()`
- Section placement: `Providers:` appears after the `Purpose:` block and before the `Howto:` block in the generated string
