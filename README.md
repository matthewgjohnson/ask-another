# ask-another

An MCP server that gives your AI assistant access to other LLMs. Query hundreds of models across OpenAI, Google, and OpenRouter through a single interface — with model discovery, usage-based favourites, and automatic enrichment (Elo ratings, pricing, knowledge cutoffs). Includes deep-research jobs and image generation across multiple model families.

## Install for Claude Desktop (CDA)

1. **Install [uv](https://docs.astral.sh/uv/)** — `brew install uv` (macOS / Linux with Homebrew) or `winget install astral-sh.uv` (Windows). See [docs/install.md](docs/install.md) for other platforms.
2. **Download** the latest `ask-another.mcpb` from [Releases](https://github.com/matthewgjohnson/ask-another/releases).
3. **Double-click** the `.mcpb` file — Claude Desktop opens an install dialog and prompts for your API keys.
4. **Paste at least one** provider key — OpenAI (`sk-…`), Google AI Studio (Gemini), or OpenRouter (`sk-or-…`). Leave the others blank.
5. **Click Enable.** First launch downloads Python dependencies via uv (~30s); after that, sub-second.

## Install for Claude Code (CC)

1. **Install [uv](https://docs.astral.sh/uv/)** — `brew install uv` (macOS / Linux with Homebrew) or `winget install astral-sh.uv` (Windows). See [docs/install.md](docs/install.md) for other platforms.
2. **Add the marketplace and install:**
   ```
   /plugin marketplace add matthewgjohnson/ask-another
   /plugin install ask-another@ask-another
   ```
3. **Enter your keys**: open `/plugin` → **ask-another** → **Configure options**, paste at least one provider key, and Save. Run `/reload-plugins` to apply.
4. **Optional**: enable auto-update at `/plugin` → **Marketplaces** → `matthewgjohnson/ask-another` so future versions install on CC startup.

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
