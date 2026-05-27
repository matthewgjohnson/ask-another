# Usage Testing Design — Recursive Self-Improvement

**Date:** 2026-03-13
**Status:** Approved
**Scope:** Two-mode testing framework: LLM peer review + scenario-based acceptance tests

## Problem

The MCP server has 10 tools, dynamic instructions, and subtle behaviors (shorthand resolution, enrichment, research lifecycle) that an AI client can misuse or misunderstand. Manual ad-hoc testing catches some issues, but there's no systematic way to:

- Detect instruction ambiguities before users hit them
- Verify tool selection works for natural language requests
- Catch regressions in shorthand resolution, error messages, or parameter handling

## Design Decisions

- **Two complementary modes** — peer review finds instruction/design gaps; scenario tests verify runtime behavior
- **Recursive self-improvement** — ask-another uses its own `completion` tool to critique itself
- **Programmatic extraction** — a script imports the actual server code and extracts real instructions + tool schemas, not hand-crafted approximations
- **Conversational execution** — tests are run by asking Claude to exercise the MCP, not automated CI
- **Growing test suite** — peer review findings feed new scenarios into Mode B

## Mode A: Peer Review (LLM Self-Critique)

### The Script

`scripts/generate_peer_review_prompt.py` — a standalone script that:

1. Imports `src.ask_another.server` directly
2. Calls `_build_instructions()` to get the exact instructions text (reads real `~/.ask-another-annotations.json`)
3. Iterates `mcp._tool_manager.list_tools()` to extract actual tool names, descriptions, and JSON parameter schemas
4. Outputs a formatted prompt ready to send to other models via `completion`

The script must call the actual server code — no recreations or approximations.

### Execution

1. Run the script to generate the prompt
2. Send the prompt to 3+ diverse models via ask-another's own `completion` tool
3. Use models from different families for diverse perspectives (e.g. one OpenAI, one DeepSeek, one GLM/Gemini)
4. Ask each model: "What could confuse an AI client? What's ambiguous? What would you test?"

### Triage

Findings are triaged into:
- **Instruction fixes** — clarify wording, add missing docs in server instructions or tool docstrings
- **New test scenarios** — add to Mode B acceptance suite
- **Code changes** — if they found a real bug or design issue

### When to Run

- Before each release
- Whenever instructions or tool schemas change
- After adding or modifying tools

## Mode B: Scenario-Based Acceptance Tests

### Categories

Seven categories, informed by the initial peer review (Kimi, DeepSeek, GLM-5):

#### 1. Tool Selection
User intent maps to correct tool. Test that natural language requests route to the right tool.

| # | User Says | Expected Tool | Why It Could Go Wrong |
|---|-----------|--------------|----------------------|
| 1 | "Ask GPT what it thinks about this code" | `completion` | Might use `start_research` for "analysis" |
| 2 | "What models can I use?" | `search_families` or `search_models` | Might skip discovery and guess |
| 3 | "Research the state of WebAssembly" | `start_research` | Might use `completion` for "research" |
| 4 | "Generate a logo for my project" | `generate_image` | Might try `completion` with an image model |
| 5 | "Remember that DeepSeek is good for creative writing" | `annotate_models` | Might just acknowledge without calling tool |
| 6 | "Is my research done yet?" | `check_research` | Might call `start_research` again |
| 7 | "Something went wrong with completion" | `feedback` | Might retry silently without reporting |

#### 2. Shorthand Resolution
Ambiguous, missing, multi-match, and cold start scenarios.

| # | Scenario | Input | Expected Behavior |
|---|----------|-------|-------------------|
| 1 | Known favourite | `model="openai"` | Resolves to most-used openai model |
| 2 | Ambiguous provider | `model="openrouter"` | Resolves to most-used openrouter model |
| 3 | Unknown shorthand | `model="anthropic"` (no anthropic provider) | Clear error with suggestion to use search_models |
| 4 | Cold start (no usage) | `model="openai"` | Falls back to highest Elo openai model |
| 5 | Full ID bypass | `model="openai/gpt-5.2"` | Routes directly, no resolution needed |

#### 3. Provider Deduplication
Same model available via multiple providers.

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | `openai/gpt-5.4` vs `openrouter/openai/gpt-5.4` in Top Rated | AI should pick based on user's configured providers |
| 2 | User asks for "GPT-5.4" | Should resolve via shorthand, not require disambiguation |
| 3 | search_models returns both variants | Results should be clear about which provider each uses |

#### 4. Parameter Edge Cases

| # | Tool | Parameter | Scenario | Expected |
|---|------|-----------|----------|----------|
| 1 | `completion` | `temperature` | Set to 0.0 | Works (valid) |
| 2 | `completion` | `temperature` | Omitted | Uses model default |
| 3 | `completion` | `temperature` | Set for model that rejects it | Clear error |
| 4 | `search_models` | `zdr` | Set to `true` | Filters to ZDR models only |
| 5 | `search_models` | `zdr` | Omitted | Uses server default |
| 6 | `generate_image` | `size` | Invalid value like "large" | Clear error |
| 7 | `generate_image` | `quality` | Invalid value | Clear error |
| 8 | `start_research` | `timeout` | Very short (5 seconds) | Returns job_id for background polling |

#### 5. Research Lifecycle

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | Start research, wait for completion | Returns full report with citations |
| 2 | Start research, timeout | Returns job_id, research continues in background |
| 3 | Check research with valid job_id | Returns results or status |
| 4 | Check research with invalid job_id | Clear error message |
| 5 | Check research with no args | Returns table of all jobs |
| 6 | Cancel running research | Job stops, confirmation returned |
| 7 | Cancel already-completed research | Clear message that job is already done |

#### 6. Instruction Interpretation
How the AI interprets the server instructions.

| # | Scenario | Risk | Expected |
|---|----------|------|----------|
| 1 | "Never guess model IDs" vs shorthand | AI refuses to use shorthand thinking it's guessing | Should understand shorthand is sanctioned |
| 2 | Call counts in favourites "(25 calls)" | AI interprets as quota/budget | Should understand as historical usage |
| 3 | "Call feedback before retrying" | AI always calls feedback before any retry | Should be guidance, not blocking |
| 4 | Favourites listed in instructions | AI calls search_models to verify them anyway | Should trust instruction-listed models |

#### 7. Error Recovery

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | Model not found | Error includes suggestion to use search_models |
| 2 | Provider API rate limit | Clear error, no infinite retry loop |
| 3 | Stale model data | refresh_models fixes it |
| 4 | Research model used with completion | Clear guidance to use start_research |
| 5 | Text model used with generate_image | Clear error about model capabilities |

### Execution

Tests are run conversationally:
1. User asks Claude to run the acceptance tests
2. Claude exercises each scenario against the live MCP
3. Results are reported: pass/fail with details
4. Failures are fixed, then re-tested

## Release Cycle

```
1. Run Mode A (peer review) → find instruction/design issues
2. Triage findings → fix instructions/code, add new Mode B scenarios
3. Run Mode B (acceptance tests) → verify runtime behavior
4. Fix any failures
5. Ship
```

## File Structure

| File | Purpose |
|------|---------|
| `scripts/generate_peer_review_prompt.py` | Extracts real instructions + tool schemas from server code |
| This spec | Design reference |

## Not Changing

- Server code (except fixes identified by testing)
- Existing unit tests
- CLAUDE.md
