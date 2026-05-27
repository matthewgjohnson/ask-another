# Provider Status Block

**Date:** 2026-05-27
**Status:** Draft
**Addresses:** Silent loss of sensitive plugin `user_config` (e.g., API keys cleared by Claude Code auto-update) leaves providers invisibly unavailable; the assistant only discovers the loss when a tool call fails.

## Problem

Sensitive plugin `user_config` values are stored in the macOS Keychain and substituted at MCP-subprocess-spawn time via `${user_config.provider_*}`. Known Claude Code auto-update bugs ([#17490](https://github.com/anthropics/claude-code/issues/17490), [#40714](https://github.com/anthropics/claude-code/issues/40714)) can clear individual values without warning. After commit `5eff401` (skip empty `PROVIDER_*` env vars instead of crashing), this loss is silent at server startup — the affected provider simply does not appear in `_provider_registry`.

The existing `Unavailable Providers:` section (introduced by the provider-health-validation spec, 2026-03-29) only surfaces providers that errored *after* being configured and used. It does not surface providers that were declared in the plugin manifest but are *missing from the runtime environment*.

Result: the assistant has no way to know at session start which expected providers are configured. Loss is discovered only when a tool call fails — exactly the scenario that prompted this design.

## Runtime layout

This section is a forcing function: before claiming the design works, verify the assumed file layout in *every* supported deployment mode. The first revision of this spec failed this check — it assumed `server.py` and the manifest live in the same tree, which is true for MCPB and local dev but **false for the Claude Code plugin install**, the exact mode that motivated the feature.

| Mode | `server.py` location | Manifest location | Discovery mechanism |
|---|---|---|---|
| Claude Code plugin | `~/.cache/uv/archive-v0/<hash>/ask_another/server.py` (uvx-installed) | `~/.claude/plugins/cache/ask-another/ask-another/<ver>/.claude-plugin/plugin.json` | `$CLAUDE_PLUGIN_ROOT` env var (auto-exported by Claude Code into MCP subprocess) |
| MCPB bundle (CDA) | `~/Library/Application Support/Claude/Claude Extensions/local.mcpb.<id>/src/ask_another/server.py` | `~/Library/Application Support/Claude/Claude Extensions/local.mcpb.<id>/manifest.json` | Walk up from `__file__` (manifest is 2 ancestor levels up) |
| Local dev (`uv run`) | `<repo>/src/ask_another/server.py` | `<repo>/manifest.json` | Walk up from `__file__` (manifest is 2 ancestor levels up) |

`CLAUDE_PLUGIN_ROOT` is the absolute path to the plugin install directory, automatically exported by Claude Code into every plugin-launched MCP subprocess's environment (per the [plugins reference](https://code.claude.com/docs/en/plugins-reference)). No changes to `manifest.json` or `plugins/ask-another/.mcp.json` are needed.

## Design

### One helper, one surfacing site

A single new helper `_provider_status()` in `src/ask_another/server.py` does two things internally: locates and parses the plugin manifest to discover declared providers, then composes that list with the existing module state (`_provider_registry`, `_provider_errors`) into a deterministic list of `(name, status_string)` pairs. `_build_instructions()` becomes a thin renderer over its output.

### Manifest location: three lookup paths

`_provider_status()` finds the manifest in this order:

1. **Explicit `manifest_path` arg** — for tests; lets a caller point directly at a fixture.
2. **`$CLAUDE_PLUGIN_ROOT` env var** — set automatically by Claude Code in the cc plugin install. The helper checks `$CLAUDE_PLUGIN_ROOT/.claude-plugin/plugin.json` then `$CLAUDE_PLUGIN_ROOT/manifest.json`, first match wins.
3. **Walk up from `Path(__file__)`** — handles MCPB and local dev, where `server.py` is co-located with the manifest (within 5 ancestor levels). Checks `manifest.json` then `.claude-plugin/plugin.json` at each level.

If no manifest is reachable through any of these paths, declared providers default to `()`. Parse failures (malformed JSON, missing `user_config`) are logged at WARNING level and treated as no-manifest.

### `_provider_status()` signature and behavior

```python
def _provider_status(
    manifest_path: Path | str | None = None,
    start_path: Path | None = None,
    *,
    max_levels: int = 5,
) -> list[tuple[str, str]]:
```

**Phase 1 — manifest discovery.** Resolves a manifest path using the three-step lookup above. If found, parses the JSON and extracts keys under `user_config` matching `^provider_(.+)$`, strips the `provider_` prefix, treats the resulting tuple as declared providers (in declaration order = manifest insertion order). Both manifest formats use `user_config` (snake_case) at the top level.

**Phase 2 — composition.** Builds the returned list by iterating, in order:

1. Each declared provider (manifest declaration order)
2. Any *extra* providers present in `_provider_registry` or `_provider_errors` (where the error value is non-`None`) but absent from the declared set — sorted alphabetically

Status string for each provider:

| State | Status string |
|---|---|
| Not in `_provider_registry` | `not configured` |
| In `_provider_registry`, no non-`None` entry in `_provider_errors` | `configured` |
| In `_provider_registry`, non-`None` entry in `_provider_errors` | `configured (error: <message>)` |

Returns an empty list when manifest, registry, and errors are all empty.

### Surfacing in `_build_instructions()`

Two changes:

1. **Insert a new `Providers:` section** between `Purpose:` and `Howto:`. Call `_provider_status()`; if the result is non-empty, append `Providers:` followed by one `  - <name>: <status>` line per pair. Omit the section entirely when the list is empty.

2. **Remove the existing `Unavailable Providers:` block** (currently around lines 849–853). The new section subsumes it: any provider with a non-`None` runtime error appears as `configured (error: <message>)` in the unified view.

Placement above `Howto:` is intentional: provider status determines what the assistant can do at all. Placement below `Purpose:` keeps the first thing the reader sees as what the server is for.

### Existing tests that need updating

Two tests in `tests/test_provider_health.py` directly assert on the `Unavailable Providers:` string that we're removing:

- `test_build_instructions_shows_unavailable_providers` — update to assert on the new `Providers:` section and the `configured (error: <msg>)` form.
- `test_full_flow_healthy_and_unhealthy` — same update.

Both updates preserve test intent ("runtime errors surface in instructions") — only the rendered shape changes.

Other tests calling `_build_instructions()` (`test_build_instructions_excludes_unhealthy_favourites`, plus four in `test_annotations.py`) assert on model identifiers or section headers we don't touch and should pass unchanged.

## Scope

### In scope

- `_provider_status()` helper in `server.py` with three-step manifest lookup (explicit arg → `$CLAUDE_PLUGIN_ROOT` → walk-up) and composed status report
- New `Providers:` section in `_build_instructions()` between `Purpose:` and `Howto:`
- Removal of the existing `Unavailable Providers:` block from `_build_instructions()`
- New tests in `tests/test_provider_config.py` covering all three lookup paths, both manifest layouts, malformed manifest, ad-hoc-extra providers, and the three status states
- Update the two affected tests in `tests/test_provider_health.py`

### Out of scope

- Changes to `manifest.json` or `plugins/ask-another/.mcp.json` — no launch-config edits needed because Claude Code already exports `CLAUDE_PLUGIN_ROOT` for free and MCPB's walk-up path is reachable from `__file__`
- Active auth probing — explicitly deferred
- Caching the discovery result beyond what happens naturally (the function runs once during module import when `_build_instructions()` is called from the `FastMCP()` constructor)
- Reading the manifest's `description` or `title` fields for richer per-provider labels
- Surfacing status anywhere other than the opening instructions (the existing `ask-another:status` skill is unchanged)
- Changes to the runtime error-recording paths (`_provider_errors` population) — consumed as-is
- Refactoring callers of `_provider_registry` / `_provider_errors` to go through `_provider_status()`

## Testing

### Manifest discovery — explicit arg

- `_provider_status(manifest_path=…)` uses the caller arg directly when the path exists
- Falls through to next lookup when the explicit path does not exist

### Manifest discovery — `$CLAUDE_PLUGIN_ROOT`

- With `CLAUDE_PLUGIN_ROOT` env var pointed at a fixture dir containing `.claude-plugin/plugin.json`, returns the declared providers
- With `CLAUDE_PLUGIN_ROOT` env var pointed at a fixture dir containing `manifest.json`, returns the declared providers
- With `CLAUDE_PLUGIN_ROOT` env var set but neither manifest file present, falls back to walk-up

### Manifest discovery — walk-up fallback

- Finds an MCPB-style `manifest.json` walking up from a stub `server.py`
- Finds a Claude Code plugin-style `.claude-plugin/plugin.json` walking up from a stub `server.py`
- Returns `[]` when no manifest is reachable within `max_levels`
- Returns `[]` and logs a warning for malformed JSON
- Returns `[]` when the manifest has no `user_config` block
- Preserves declaration order from the manifest

### Composition

- Declared providers with binary configured/not-configured statuses
- Runtime error produces the `configured (error: …)` form
- A declared provider with both a registry entry AND an error string reports the error form
- Ad-hoc providers (in registry or errors but not declared) appended after the declared ones in alphabetical order
- An undeclared-but-errored provider still appears in the output
- `_provider_errors[name] = None` does NOT trigger the error form

### Rendering in `_build_instructions()`

- Includes the `Providers:` section when `_provider_status()` returns a non-empty list
- Omits the section entirely when `_provider_status()` returns `[]`
- Section appears between `Purpose:` and `Howto:`
- The old `Unavailable Providers:` block does not appear in the rendered output even when `_provider_errors` has entries
- Renders the `configured (error: …)` form when the helper returns it

### Updated existing tests

- `test_build_instructions_shows_unavailable_providers` in `tests/test_provider_health.py`: assert `Providers:` + `gemini: configured (error: Google API key is required)` instead of the removed strings
- `test_full_flow_healthy_and_unhealthy` in `tests/test_provider_health.py`: same shape update
