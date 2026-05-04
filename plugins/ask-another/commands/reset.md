---
description: Clear all ask-another keys and settings (asks for confirmation)
allowed-tools: Read, Write
---

The user invoked `/ask-another:reset`. Wipe the plugin's configuration block.

1. Ask the user, then wait for a reply: "Clear all ask-another keys and toggles? This removes the `pluginConfigs[\"ask-another@ask-another\"]` entry from `~/.claude/settings.json`. (yes/no)"
2. If they don't reply with `yes` (case-insensitive), print "Cancelled." and stop.
3. Read `~/.claude/settings.json`.
4. If `pluginConfigs["ask-another@ask-another"]` exists, delete that key. If `pluginConfigs` becomes empty, you may delete the parent key too.
5. Write the file back.
6. Print: "Cleared. Run `/reload-plugins` to apply, then `/ask-another:status` to confirm."
