#!/usr/bin/env python3
"""Generate the peer review prompt from actual server code.

Extracts the real MCP instructions and tool schemas from the running
server module — no hand-crafted approximations.

Usage:
    PROVIDER_OPENAI="openai;sk-dummy" uv run python scripts/generate_peer_review_prompt.py

At least one PROVIDER_* env var is required for module import, but no
API calls are made. Use a dummy key if you don't need real annotations.
"""

import ask_another.server as server


def main():
    # 1. Get the exact instructions a client sees
    instructions = server._build_instructions()

    # 2. Get all tool metadata from the real FastMCP instance
    tools = server.mcp._tool_manager.list_tools()

    tool_descriptions = []
    for i, tool in enumerate(tools, 1):
        params = tool.parameters.get("properties", {})
        required = tool.parameters.get("required", [])

        param_parts = []
        for name, schema in params.items():
            # Skip the injected context parameter
            if name == tool.context_kwarg:
                continue
            type_str = schema.get("type", "any")
            if "anyOf" in schema:
                types = [
                    t.get("type", "?")
                    for t in schema["anyOf"]
                    if t.get("type") != "null"
                ]
                type_str = types[0] if types else "any"
            optional = "" if name in required else "?"
            param_parts.append(f"{name}{optional}: {type_str}")

        param_str = ", ".join(param_parts)
        desc = tool.description.strip()
        tool_descriptions.append(f"{i}. **{tool.name}**({param_str})\n   \"{desc}\"")

    # 3. Format the complete prompt
    tool_count = len(tool_descriptions)
    tools_block = "\n\n".join(tool_descriptions)

    prompt = f"""I'm building an MCP server called "ask-another" that lets AI assistants \
query other LLMs. Below are the exact server instructions that an MCP client (like Claude) \
sees at startup, followed by all {tool_count} tool descriptions with their parameters.

I'm designing acceptance tests to catch scenarios where the AI client could get confused, \
misuse tools, or have a bad experience.

Please review these instructions and tool descriptions carefully, then tell me:
1. What scenarios could confuse an AI client using this MCP?
2. What edge cases, ambiguities, or pitfalls would you test for?
3. What's missing or unclear in the instructions that could lead to mistakes?

Be specific — reference exact tool names, parameter names, and instruction text where relevant.

---

SERVER INSTRUCTIONS (shown to AI client at startup):

```
{instructions}
```

TOOL DESCRIPTIONS:

{tools_block}"""

    print(prompt)


if __name__ == "__main__":
    main()
