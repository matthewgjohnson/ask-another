---
description: Set or update ask-another API keys and toggles via native prompts
allowed-tools: Bash
---

The user invoked `/ask-another:configure`. Run the script below verbatim. It shows a sequence of native macOS prompts (`osascript`) for each API key and toggle, captures values directly inside the subprocess, and writes them to `~/.claude/settings.json`. **The script never prints key values; you do not see them; they never enter chat context.**

Run this exact Bash command (do not modify, do not split, do not echo any output you receive other than to relay it to the user):

```bash
python3 <<'PYEOF'
import json, os, subprocess, sys

SETTINGS = os.path.expanduser("~/.claude/settings.json")
PLUGIN_KEY = "ask-another@ask-another"


def load_settings():
    if not os.path.exists(SETTINGS):
        return {}
    try:
        with open(SETTINGS) as f:
            return json.load(f)
    except json.JSONDecodeError:
        sys.exit(f"ERROR: {SETTINGS} is not valid JSON; aborting.")


def save_settings(data):
    with open(SETTINGS, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def prompt_secret(title, message):
    """Show a native macOS password-style dialog. Returns the value or None if cancelled."""
    script = (
        f'display dialog "{message}" with title "{title}" '
        f'default answer "" with hidden answer '
        f'buttons {{"Skip", "Save"}} default button "Save"'
    )
    result = subprocess.run(
        ["osascript", "-e", script, "-e", 'text returned of result & "|" & button returned of result'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None  # user cancelled / closed
    out = result.stdout.strip()
    if "|" not in out:
        return None
    value, button = out.rsplit("|", 1)
    if button.strip() != "Save":
        return None
    return value or None  # blank = treat as skip


def prompt_bool(title, message, current):
    """Yes/No dialog with current value as default."""
    default = "Yes" if current else "No"
    script = (
        f'display dialog "{message}\\n\\nCurrent: {current}" with title "{title}" '
        f'buttons {{"Yes", "No"}} default button "{default}"'
    )
    result = subprocess.run(
        ["osascript", "-e", script, "-e", 'button returned of result'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return current  # user cancelled — keep current
    return result.stdout.strip() == "Yes"


def status(name, options):
    v = options.get(name)
    if not isinstance(v, str) or not v or "PASTE_" in v:
        return "Not set"
    return f"Configured (***{v[-4:]})"


def main():
    data = load_settings()
    options = (
        data.setdefault("pluginConfigs", {})
            .setdefault(PLUGIN_KEY, {})
            .setdefault("options", {})
    )

    print("ask-another: configure providers (a native dialog will appear for each)\n")

    for key, label in [
        ("provider_openai", "OpenAI API key"),
        ("provider_gemini", "Gemini API key"),
        ("provider_openrouter", "OpenRouter API key"),
    ]:
        existing = status(key, options)
        msg = f"{label} (current: {existing})\\nLeave blank or click Skip to keep as-is."
        new_value = prompt_secret("ask-another", msg)
        if new_value is not None:
            options[key] = new_value
            print(f"  {key}: saved")
        else:
            print(f"  {key}: kept ({existing})")

    options["zero_data_retention"] = prompt_bool(
        "ask-another", "Filter OpenRouter to ZDR-compatible models only?",
        options.get("zero_data_retention", True),
    )
    print(f"  zero_data_retention: {options['zero_data_retention']}")

    options["open_generated_images"] = prompt_bool(
        "ask-another", "Auto-open generated images in your image viewer?",
        options.get("open_generated_images", True),
    )
    print(f"  open_generated_images: {options['open_generated_images']}")

    save_settings(data)
    print("\nSaved. Run /reload-plugins to apply, then /ask-another:status to verify.")


if __name__ == "__main__":
    main()
PYEOF
```

After the command finishes, relay its output (status lines only — no key values appear in the output) and remind the user to run `/reload-plugins`.
