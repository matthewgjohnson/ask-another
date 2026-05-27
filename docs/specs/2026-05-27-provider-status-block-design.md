# Provider Status Block

**Date:** 2026-05-27
**Status:** Draft
**Addresses:** Silent loss of sensitive plugin `user_config` (e.g., API keys cleared by Claude Code auto-update) leaves providers invisibly unavailable; the assistant only discovers the loss when a tool call fails.

## Problem

Sensitive plugin `user_config` values are stored in the macOS Keychain and substituted at MCP-subprocess-spawn time via `${user_config.provider_*}`. Known Claude Code auto-update bugs ([#17490](https://github.com/anthropics/claude-code/issues/17490), [#40714](https://github.com/anthropics/claude-code/issues/40714)) can clear individual values without warning. After commit `5eff401` (skip empty `PROVIDER_*` env vars instead of crashing), this loss is silent at server startup — the affected provider simply does not appear in `_provider_registry`.

The existing `Unavailable Providers:` section (introduced by the provider-health-validation spec, 2026-03-29) only surfaces providers that errored *after* being configured and used. It does not surface providers that were declared in the plugin manifest but are *missing from the runtime environment*.

Result: the assistant has no way to know at session start which expected providers are configured. Loss is discovered only when a tool call fails — exactly the scenario that prompted this design.

## Design

### One helper, one surfacing site

A single new helper `_provider_status()` in `src/ask_another/server.py` does two things internally: walks the plugin manifest to discover declared providers, then composes that list with the existing module state (`_provider_registry`, `_provider_errors`) into a deterministic list of `(name, status_string)` pairs. `_build_instructions()` becomes a thin renderer over its output.

This is deliberately a single function rather than two layered helpers. The manifest walk and the composition are both small, both internal, and both serve exactly one caller. Splitting them into separate functions would create artificial API surface for no real testability win (tests cover the unified function by varying `start_path` and module state).

### `_provider_status()` — manifest walk + composed status report

Signature:

```python
def _provider_status(
    start_path: Path | None = None, *, max_levels: int = 5
) -> list[tuple[str, str]]:
```

Behavior, in two internal phases:

**Phase 1 — manifest discovery.** Walks up from `start_path` (default: `Path(__file__).resolve()`) at most `max_levels` ancestor directories, looking for either:

- `manifest.json` (MCPB bundle layout — combines schema + env wiring in one file), OR
- `.claude-plugin/plugin.json` (Claude Code plugin layout — schema in `plugin.json`, env wiring in a sibling `.mcp.json`)

First match wins. Both formats use `user_config` (snake_case) at the top level. The helper parses the JSON, extracts keys under `user_config` matching `^provider_(.+)$`, strips the `provider_` prefix, and treats the resulting tuple in declaration order (Python dict iteration order = manifest insertion order) as the declared providers.

If no manifest is reachable, the JSON is malformed, or `user_config` is missing, the declared tuple is `()`. Parse failures are logged at WARNING level.

The plugin spec's `user_config` schema is constrained to a flat list of named scalar fields (no arrays, no conditionals — see [plugins-reference](https://code.claude.com/docs/en/plugins-reference)), so the manifest is the only declarative file that already enumerates which providers the plugin supports. Duplicating the list in `server.py` would create lockstep editing across two files for every provider added.

**Phase 2 — composition.** Builds the returned list by iterating, in order:

1. Each declared provider (manifest declaration order)
2. Any *extra* providers present in `_provider_registry` (ad-hoc env var like `PROVIDER_ANTHROPIC=…` set outside the manifest) or `_provider_errors` (runtime failure for a non-declared provider) but absent from the declared set — sorted alphabetically

The status string for each provider is one of three values:

| State | Status string |
|---|---|
| Not in `_provider_registry` | `not configured` |
| In `_provider_registry`, no non-`None` entry in `_provider_errors` | `configured` |
| In `_provider_registry`, non-`None` entry in `_provider_errors` | `configured (error: <message>)` |

Returns an empty list when manifest, registry, and errors are all empty (e.g., local dev mode with no manifest reachable and no configured providers).

### Surfacing in `_build_instructions()`

Two changes inside `_build_instructions()`:

1. **Insert a new `Providers:` section** between the existing `Purpose:` and `Howto:` blocks. The function calls `_provider_status()` and, if the result is non-empty, appends a section like:

   ```
   Providers:
     - openai: configured
     - gemini: configured
     - openrouter: not configured
   ```

   Or with a runtime error:

   ```
   Providers:
     - openai: configured
     - gemini: configured (error: Google API key is required. ...)
     - openrouter: configured
   ```

   The section is omitted entirely when `_provider_status()` returns `[]`.

2. **Remove the existing `Unavailable Providers:` block** (currently around lines 849–853). The new section subsumes it: any provider with a non-`None` runtime error now appears as `configured (error: <message>)` in the unified view. Removing the separate block eliminates double-listing for failed providers and reduces the number of moving parts in the instructions string.

The underlying `_provider_errors` state and the runtime code paths that populate it (in `_refresh_provider_models()`, `search_models`, `search_families`, and the tool entry points) are unchanged — only the rendering changes.

Placement above `Howto:` is intentional: provider status determines what the assistant can do at all. Surfacing it before the usage instructions is more useful than burying it below the model lists. Placement below `Purpose:` keeps the first thing the reader sees as what the server is for.

## Scope

### In scope

- `_provider_status()` helper in `server.py` covering manifest walk (MCPB + Claude Code plugin layouts) and composed status report
- New `Providers:` section in `_build_instructions()` between `Purpose:` and `Howto:`
- Removal of the existing `Unavailable Providers:` block from `_build_instructions()`
- Tests in `tests/test_provider_config.py` covering both manifest layouts, malformed-manifest handling, ad-hoc-extra providers, and the three status states

### Out of scope

- Active auth probing — explicitly deferred; user preference is the cheap env-var check until/unless the loss pattern repeats with valid-but-broken keys
- Caching the discovery result beyond what happens naturally (the function runs once during module import when `_build_instructions()` is called from the `FastMCP()` constructor)
- Reading the manifest's `description` or `title` fields to produce richer per-provider labels
- Surfacing status anywhere other than the opening instructions (e.g., as a separate MCP tool or skill — the existing `ask-another:status` skill is unchanged)
- Changes to the runtime error-recording paths (`_provider_errors` population) — consumed as-is
- Refactoring callers of `_provider_registry` / `_provider_errors` to go through `_provider_status()` — `_provider_status()` is a presentation layer, not a replacement for the underlying state

## Testing

Extend `tests/test_provider_config.py` with the following.

### Manifest discovery behavior (varying `start_path`, empty state)

- Finds and parses an MCPB-style `manifest.json` placed in a fixture directory above a stub `server.py`, returning declared names in manifest order
- Finds and parses a Claude Code plugin-style `.claude-plugin/plugin.json` in the same setup
- Returns `[]` when no manifest is reachable within the walk-up cap
- Returns `[]` and logs a warning for malformed JSON
- Returns `[]` when the manifest has no `user_config` block
- Preserves declaration order from the manifest

### Composition behavior (known manifest fixture + varied state)

- Declared providers with binary configured/not-configured statuses
- Runtime error produces the `configured (error: …)` form
- A declared provider with both a registry entry AND an error string reports the error form, not `configured`
- Ad-hoc providers (in registry or errors but not declared) appended after the declared ones in alphabetical order
- An undeclared-but-errored provider still appears in the output
- `_provider_errors[name] = None` does NOT trigger the error form

### Rendering in `_build_instructions()` (monkeypatch `_provider_status()` directly)

- Includes the `Providers:` section when `_provider_status()` returns a non-empty list
- Omits the section entirely when `_provider_status()` returns `[]`
- Section appears between `Purpose:` and `Howto:`
- The old `Unavailable Providers:` block does not appear in the rendered output even when `_provider_errors` has entries
- Renders the `configured (error: …)` form when the helper returns it
