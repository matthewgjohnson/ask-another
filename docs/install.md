# Installation

## Install uv

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. Install it with your platform's package manager:

| Platform | Command |
|----------|---------|
| macOS | `brew install uv` |
| Arch Linux | `pacman -S uv` |
| Fedora | `dnf install uv` |
| Windows | `winget install astral-sh.uv` |

`uv` is not in the default Debian/Ubuntu apt repos. For Ubuntu, use `snap install uv` or `brew install uv` ([Homebrew on Linux](https://brew.sh/)). See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for all options.

## Client Setup

### Claude Desktop

Config file location:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add the following to your config file:

```json
{
  "mcpServers": {
    "ask-another": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
      "env": {
        "PROVIDER_OPENAI": "openai;sk-your-openai-key",
        "PROVIDER_GEMINI": "gemini;your-google-key",
        "PROVIDER_OPENROUTER": "openrouter;sk-or-your-openrouter-key"
      }
    }
  }
}
```

At least one provider is required. Remove any you don't have keys for.

Restart Claude Desktop after saving.

### Claude Code

```bash
claude mcp add ask-another \
  -e PROVIDER_OPENAI="openai;sk-your-key" \
  -e PROVIDER_GEMINI="gemini;your-key" \
  -e PROVIDER_OPENROUTER="openrouter;sk-or-your-key" \
  -- uvx --from git+https://github.com/matthewgjohnson/ask-another ask-another
```

### Other Clients

<details>
<summary>Cursor</summary>

Go to **Settings > Features > MCP > Add New MCP Server**. Set:
- **Command:** `uvx`
- **Args:** `--from git+https://github.com/matthewgjohnson/ask-another ask-another`

Add provider environment variables in the server's env section.

See [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol) for details.
</details>

<details>
<summary>Windsurf</summary>

Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "ask-another": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
      "env": {
        "PROVIDER_OPENAI": "openai;sk-your-key"
      }
    }
  }
}
```
</details>

<details>
<summary>Cline / Roo Code (VS Code)</summary>

Open the MCP tab in the extension sidebar and add a server with the same JSON structure as the Claude Desktop config above.
</details>

<details>
<summary>Zed</summary>

Add to your Zed `settings.json` under `context_servers`:

```json
{
  "context_servers": {
    "ask-another": {
      "command": {
        "path": "uvx",
        "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
        "env": {
          "PROVIDER_OPENAI": "openai;sk-your-key"
        }
      }
    }
  }
}
```
</details>

## Configuration

All options go in the `env` block of your MCP client config.

### Providers

Format: `PROVIDER_<NAME>="provider-name;api-key"`

At least one provider is required. Models are discovered dynamically from each provider's API — no need to list individual models.

| Variable | Example |
|----------|---------|
| `PROVIDER_OPENAI` | `openai;sk-your-key` |
| `PROVIDER_GEMINI` | `gemini;your-key` |
| `PROVIDER_OPENROUTER` | `openrouter;sk-or-your-key` |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `CACHE_TTL_MINUTES` | `360` | How often to re-scan providers and re-fetch enrichment (minutes) |
| `ZERO_DATA_RETENTION` | enabled | Filter OpenRouter to ZDR-compatible models only. Set to `false` to disable |
| `LOG_LEVEL` | *(disabled)* | Enable file logging: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `~/.ask-another.log` | Log file path |
| `LOG_FILE_SIZE` | `5` | Max log file size in MB |
| `LOG_FILE_COUNT` | `2` | Number of rotation backups |
| `IMAGE_OUTPUT_DIR` | `~/Pictures/ask-another` | Where generated images are saved |
| `ANNOTATIONS_FILE` | `~/.ask-another-annotations.json` | Model metadata, usage, and notes |
| `FEEDBACK_LOG` | `~/.ask-another-feedback.jsonl` | Feedback log path |
