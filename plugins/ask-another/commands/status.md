---
description: Show which ask-another providers are configured and reachable
allowed-tools: Read, mcp__plugin_ask-another_ask-another__search_families
---

The user invoked `/ask-another:status`. Report what's currently configured. **Never display key values; only show the last 4 characters as a fingerprint.**

1. Read `~/.claude/settings.json`. If missing or empty, treat options as `{}`.
2. Locate `pluginConfigs["ask-another@ask-another"].options` (may not exist).
3. For each of `provider_openai`, `provider_gemini`, `provider_openrouter`:
   - If present and non-empty and not the placeholder string `PASTE_..._KEY_HERE`: report `Configured (***<last 4 chars>)`.
   - Else: report `Not set`.
4. For `zero_data_retention` and `open_generated_images`: report the boolean, or `(default: true)` if missing.
5. If at least one provider is configured (and not a placeholder), call `mcp__plugin_ask-another_ask-another__search_families` and append a one-line "Reachability: N family lines returned" — this confirms the MCP server is live and using the keys.
6. End with: "Edit with /ask-another:configure. Run /reload-plugins after any settings change."
