# Usage Testing Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the peer review prompt generator script that extracts real server instructions and tool schemas programmatically.

**Architecture:** Single script that imports the server module directly and outputs a formatted prompt for LLM critique.

**Tech Stack:** Python, imports from `ask_another.server`

**Spec:** `docs/superpowers/specs/2026-03-13-usage-testing-design.md`

---

## Chunk 1: Peer Review Script

### Task 1: Create scripts/generate_peer_review_prompt.py

**Files:**
- Create: `scripts/generate_peer_review_prompt.py`

- [ ] **Step 1: Write the script**

The script must:
1. Import `ask_another.server` to access the real server objects
2. Call `server._build_instructions()` to get the exact instructions text
3. Iterate `server.mcp._tool_manager.list_tools()` to get all tool metadata
4. Format each tool as: name, parameters (from JSON schema), description
5. Combine into a single prompt with the system instruction for QA review
6. Print the prompt to stdout

```python
#!/usr/bin/env python3
"""Generate the peer review prompt from actual server code.

Extracts the real MCP instructions and tool schemas from the running
server module — no hand-crafted approximations.

Usage:
    uv run python scripts/generate_peer_review_prompt.py
"""

import json
import sys

# Import the actual server module — this loads config and annotations
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
                types = [t.get("type", "?") for t in schema["anyOf"] if t.get("type") != "null"]
                type_str = types[0] if types else "any"
            optional = "" if name in required else "?"
            param_parts.append(f"{name}{optional}: {type_str}")

        param_str = ", ".join(param_parts)
        desc = tool.description.strip()
        tool_descriptions.append(f"{i}. **{tool.name}**({param_str})\n   \"{desc}\"")

    # 3. Format the complete prompt
    prompt = f"""I'm building an MCP server called "ask-another" that lets AI assistants query other LLMs. Below are the exact server instructions that an MCP client (like Claude) sees at startup, followed by all {len(tools)} tool descriptions with their parameters.

I'm designing acceptance tests to catch scenarios where the AI client could get confused, misuse tools, or have a bad experience.

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

{chr(10).join(tool_descriptions)}"""

    print(prompt)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the script runs and produces output**

Run: `PROVIDER_OPENAI="openai;sk-dummy" uv run python scripts/generate_peer_review_prompt.py`

Expected: prints the full prompt with real instructions text and all 10 tool descriptions. The provider env var is needed for module import but no API calls are made.

Check:
- Instructions section contains "Purpose:", "Howto:", and any favourites/Elo/recent sections
- All 10 tools are listed with their actual descriptions and parameters
- No `ctx` parameter appears (filtered out)

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_peer_review_prompt.py
git commit -m "feat: add peer review prompt generator for recursive LLM testing"
```

---

## Chunk 2: Verification

### Task 2: End-to-end test of Mode A

- [ ] **Step 1: Generate the prompt**

Run: `PROVIDER_OPENAI="openai;sk-dummy" uv run python scripts/generate_peer_review_prompt.py > /tmp/peer-review-prompt.txt`

- [ ] **Step 2: Verify prompt content**

Check that `/tmp/peer-review-prompt.txt` contains:
- The actual `_build_instructions()` output (with real favourites if annotations exist)
- All 10 tool names: search_families, search_models, completion, annotate_models, refresh_models, feedback, start_research, check_research, cancel_research, generate_image
- Parameter types and optional markers
- No internal parameters (ctx)

- [ ] **Step 3: Send to a model via ask-another**

Use the generated prompt with `completion` to verify the full loop works:
the prompt can be copied and sent to any model for critique.

---

## Chunk 3: Run full test suite

### Task 3: Verify nothing broke

- [ ] **Step 1: Run all tests**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 2: Push**

```bash
git push
```
