# ask-another

An MCP server that gives your AI assistant access to other LLMs. Query hundreds of models across OpenAI, Google, and OpenRouter through a single interface — with model discovery, usage-based favourites, and automatic enrichment (Elo ratings, pricing, knowledge cutoffs). Includes deep-research jobs and image generation across multiple model families.

## Quick Start (Claude Desktop)

1. **Download** the latest `ask-another.mcpb` from [Releases](https://github.com/matthewgjohnson/ask-another/releases).
2. **Double-click** the `.mcpb` file. Claude Desktop opens an install dialog.
3. **Paste your API keys** into the prompts (any one is enough — leave others blank to skip):
   - OpenAI key (starts with `sk-`)
   - Google AI Studio key (Gemini)
   - OpenRouter key (starts with `sk-or-`)
4. **Click Enable.** First launch downloads dependencies (~30s with progress UI); after that, sub-second.

Done. The 10 tools (see below) are now available to Claude Desktop.

## Other MCP clients (Claude Code, Cursor, Windsurf, …)

These clients don't install `.mcpb` files. Add the server to your client's MCP config manually. Example for Claude Code (`~/.claude.json`):

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

Requires [uv](https://docs.astral.sh/uv/) on PATH (`brew install uv` on macOS). Provider entries are optional individually — at least one is needed.

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
make dxt          # builds ask-another.mcpb
```

Then double-click the `.mcpb` to install in Claude Desktop.

## License

[MIT](LICENSE)
