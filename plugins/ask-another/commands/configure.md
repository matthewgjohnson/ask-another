---
description: Set or update ask-another API keys and toggles (opens settings file)
allowed-tools: Read, Edit, Write, Bash
---

The user invoked `/ask-another:configure`. Goal: land them in `~/.claude/settings.json` with the right `pluginConfigs["ask-another@ask-another"].options` block already in place, so they paste their own keys. **Never read, echo, log, or quote any API key values you encounter.**

1. Read `~/.claude/settings.json`. If missing or empty, treat current data as `{}`.
2. Ensure `pluginConfigs["ask-another@ask-another"].options` exists. For each of the five fields below, **only** insert a placeholder if the field is not already set. Do not overwrite existing values. Do not display existing values.
   - `provider_openai` → string `"PASTE_OPENAI_KEY_HERE"`
   - `provider_gemini` → string `"PASTE_GEMINI_KEY_HERE"`
   - `provider_openrouter` → string `"PASTE_OPENROUTER_KEY_HERE"`
   - `zero_data_retention` → boolean `true`
   - `open_generated_images` → boolean `true`
3. Write `~/.claude/settings.json` back, preserving the rest of the file's structure and formatting.
4. Run `open -t ~/.claude/settings.json` to open the file in TextEdit.
5. Print exactly:
   ```
   Settings file open. Replace each PASTE_..._KEY_HERE placeholder with the
   actual key, or delete the line entirely if you don't have a key for that
   provider. Save the file, then run /reload-plugins and /ask-another:status.
   ```
