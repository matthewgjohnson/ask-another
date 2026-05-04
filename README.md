# ask-another

An MCP server that gives your AI assistant access to other LLMs. Query hundreds of models across OpenAI, Google, and OpenRouter through a single interface — with model discovery, usage-based favourites, and automatic enrichment (Elo ratings, pricing, knowledge cutoffs). Includes deep-research jobs and image generation across multiple model families.

## Prerequisite

[uv](https://docs.astral.sh/uv/). Install via `brew install uv` (macOS / Linux with Homebrew) or `winget install astral-sh.uv` (Windows). See [docs/install.md](docs/install.md) for distro-specific options.

## Quick Start (Claude Desktop)

1. **Download** the latest `ask-another.mcpb` from [Releases](https://github.com/matthewgjohnson/ask-another/releases).
2. **Double-click** the `.mcpb` file. Claude Desktop opens an install dialog.
3. **Paste your API keys** into the prompts (any one is enough — leave others blank to skip):
   - OpenAI key (starts with `sk-`)
   - Google AI Studio key (Gemini)
   - OpenRouter key (starts with `sk-or-`)
4. **Click Enable.** First launch downloads dependencies (~30s with progress UI); after that, sub-second.

Done. The 10 tools (see below) are now available to Claude Desktop.

## Quick Start (Claude Code)

This repo doubles as a Claude Code plugin marketplace. Install in two steps:

```
/plugin marketplace add matthewgjohnson/ask-another
/plugin install ask-another@ask-another
```

Then enter your keys: open `/plugin` → **ask-another** → **Configure options**, paste any one provider key (others can stay blank), and Save. Run `/reload-plugins` to apply.

To get future updates without uninstall/reinstall, enable auto-update from `/plugin` → **Marketplaces** → `matthewgjohnson/ask-another`. Off by default for third-party marketplaces.

## Other MCP clients (Cursor, Windsurf, …)

For clients without MCPB or plugin support, add the server manually. Example config:

```json
{
  "mcpServers": {
    "ask-another": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/matthewgjohnson/ask-another", "ask-another"],
      "env": {
        "PROVIDER_OPENAI": "sk-your-openai-key",
        "PROVIDER_GEMINI": "your-google-key",
        "PROVIDER_OPENROUTER": "sk-or-your-openrouter-key"
      }
    }
  }
}
```

## What You Can Do

- "Ask GPT-5.2 what it thinks about this architecture" → `completion`
- "What Gemini models are available?" → `search_models`
- "Research the state of WebAssembly in 2026" → `start_research`
- "Generate a logo for my project" → `generate_image`
- "Note that DeepSeek is good for creative writing" → `annotate_models`

See all 10 tools in the [Reference](docs/reference.md).

## Learn More

- **[Installation Guide](docs/install.md)** — Linux/Windows setup, Claude Code, Cursor, Windsurf, and other MCP clients, all configuration options
- **[Reference](docs/reference.md)** — tools, annotations & enrichment, architecture, development

## Building from source

```bash
git clone https://github.com/matthewgjohnson/ask-another
cd ask-another
make mcpb         # builds ask-another.mcpb
```

Then double-click the `.mcpb` to install in Claude Desktop.

## License

[MIT](LICENSE)
