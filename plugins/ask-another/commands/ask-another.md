---
description: Manage ask-another (configure API keys, check status, reset)
argument-hint: [configure | status | reset]
allowed-tools: Read, Edit, Write, Bash, mcp__plugin_ask-another_ask-another__search_families
---

The user has invoked `/ask-another $ARGUMENTS`. This is a dispatcher for plugin
configuration and status. Treat anything in the user's chat input verbatim —
**never read, echo, log, or quote API key values you encounter while working;
they live in `~/.claude/settings.json` under
`pluginConfigs["ask-another@ask-another"].options` and must stay there**.

Branch on `$ARGUMENTS`:

## No args, or `help`

Print this menu and stop:

```
ask-another — query other AI models from Claude Code

Usage:
  /ask-another configure   Set or update API keys and toggles (opens settings file)
  /ask-another status      Show which providers are configured
  /ask-another reset       Clear all ask-another settings (asks for confirmation)

After any change, run /reload-plugins to apply.
```

## `status`

1. Read `~/.claude/settings.json`. If missing or empty, treat options as `{}`.
2. Locate `pluginConfigs["ask-another@ask-another"].options` (may not exist).
3. For each of `provider_openai`, `provider_gemini`, `provider_openrouter`:
   - If present and non-empty: report `Configured (***<last 4 chars>)`. Use only the LAST 4 characters; never display more.
   - Else: report `Not set`.
4. For `zero_data_retention` and `open_generated_images`: report the boolean, or `(default: true)` if missing.
5. If at least one provider is configured, call `mcp__plugin_ask-another_ask-another__search_families` and report how many provider-family lines come back, as a reachability check.
6. End with: "Tip: run `/reload-plugins` after any settings change."

## `configure`

The goal is to land the user in their settings file with the right block already present so they paste keys themselves — keys never enter the chat.

1. Read `~/.claude/settings.json` (create with `{}` if missing).
2. Ensure `pluginConfigs["ask-another@ask-another"].options` exists. For any field that is **not already set**, insert one of these placeholders:
   - string fields → `"PASTE_<NAME>_KEY_HERE"`
   - boolean fields → `true` (the safe default)
   Do not overwrite any existing values you find. Never echo any existing values back to the user.
3. Write the updated settings.json (preserving formatting where possible).
4. Run `open -t ~/.claude/settings.json` to open the file in TextEdit.
5. Tell the user:
   ```
   Settings file open. Replace each PASTE_..._KEY_HERE placeholder with the
   actual key, or delete the line entirely if you don't have a key for that
   provider. Save the file, then run /reload-plugins and /ask-another status.
   ```

## `reset`

1. Ask the user: "Clear all ask-another keys and toggles? This removes the `pluginConfigs[\"ask-another@ask-another\"]` entry from settings.json. (yes/no)"
2. If they answer yes: read settings.json, delete the entry, write back.
3. Confirm: "Cleared. Run `/reload-plugins` to apply."

## Anything else

If `$ARGUMENTS` doesn't match `configure`, `status`, `reset`, or `help`, print the help menu (same as no args) and stop.
