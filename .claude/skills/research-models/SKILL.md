---
name: research-models
description: Research the model landscape and generate a model report
allowed-tools: WebSearch, WebFetch, Read, Write, Glob, Grep, AskUserQuestion, mcp__ask-another__search_families, mcp__ask-another__search_models, mcp__ask-another__start_research, mcp__ask-another__check_research, mcp__ask-another__cancel_research
model: opus
---

You are researching the current LLM model landscape to produce a comprehensive model report. Work through three stages, pausing for user approval between each.

**Important: Rank models by current data, not historical reputation.** The landscape changes fast. Cross-check Arena Elo, benchmark scores, and pricing before assigning positions. Do not assume any provider is the default #1 — let the numbers decide.

**ZDR filtering is active by default.** The `search_families` and `search_models` tools filter OpenRouter models to those with guaranteed Zero Data Retention. Models without ZDR (e.g. xAI/Grok) will not appear in the catalog. Do not research, recommend, or include non-ZDR models in the report or data file — they cannot be used.

# Stage 1: Survey

Goal: Discover the best ranking sources, pull available models, and build a ranked shortlist of the top 5-10 models worth deep-diving on.

1. **Gather ranking sources.** Start with these three proven sources, then use WebSearch to discover 1-2 additional current leaderboards worth consulting:
   - **artificialanalysis.ai/leaderboards/models** — independent quality, speed, and cost benchmarks
   - **arena.ai/leaderboard** — human preference Elo scores (overall, coding, math, creative writing)
   - **openrouter.ai/rankings** — real-world usage and popularity data
2. **Fetch the ranking sources.** Use WebFetch to pull the top models from each source (the three above plus any new ones discovered). Extract model names, scores, and any pricing/speed data available. **Collect the four standard metrics (aa_index, arena_elo, swe_bench, gpqa) for as many models as possible at this stage** — not just the shortlist. Also grab tok_sec and pricing where available. This data populates the data file later; sparse rows are less useful.
3. **Pull available models.** Call `search_families` (no arguments) and `search_models` (no arguments) to get the full catalog of models available through ask-another.
4. **Cross-reference.** Match ranked models against the available catalog. Identify the top 5-10 candidates for deep research. Note all other models that appeared in any ranking — these will get quick summaries later.
5. **Present the shortlist.** Show the ranked shortlist to the user with a brief rationale for each pick. Ask the user to approve, add, or remove models before proceeding.

# Stage 2: Deep Research

Goal: Build a detailed profile for each approved model.

For each model in the approved shortlist, research using WebSearch + WebFetch (no API cost). For each model, run 3-4 targeted searches:

1. **Benchmarks and specs:** Search for `"model-name benchmarks SWE-bench GPQA pricing 2026"`. Fetch the Artificial Analysis model page (e.g. `artificialanalysis.ai/models/model-name`) for standardised metrics.
2. **Community reception:** Search for `"model-name review developer experience"` to find real-world feedback.
3. **Fill metric gaps:** Search specifically for any missing PSV fields — e.g. `"model-name tokens per second"` or `"model-name Arena Elo"`. **Sparse rows in the data file are a sign of incomplete research.**

For each model, collect:
   - What it's best at and its known weaknesses
   - Community consensus and how it compares to similar models
   - **Specific numbers for the data file:** context window, tokens/sec, price per M input/output tokens, AA Intelligence Index score, Arena Elo, SWE-bench Verified %, GPQA Diamond %

**Optional: deep research.** If the user requests it or budget allows, use `start_research` with `openrouter/perplexity/sonar-deep-research` (~$1/query, ~$10-12 for a full run) for richer profiles. Use `check_research` to poll if it times out. This is a quality upgrade, not the default.

# Stage 3: Recommend Favourites + Write Report

Goal: Pick 3-5 recommended favourites and write the final report.

1. From the research, select 3-5 models as recommended favourites:
   - One per provider family (e.g. one OpenAI, one Google, one open-source via OpenRouter)
   - Cover diverse use cases (coding, reasoning, creative, research)
   - Balance quality against cost/speed
2. Present your favourite recommendations with rationale. Ask the user to approve before writing.
3. Write the markdown report using the structure below.
4. Write the data file (`docs/models.psv`) using the data file format below. Include ALL models surveyed (not just the shortlist). Sort by `aa_index` descending. Models without an `aa_index` score go at the bottom.

# Report Structure

Write the report as a markdown file. Ask the user where to save it, or default to `docs/model-report.md`.

The report has four layers, each zooming out. A reader can stop at the level of detail they need.

```
# Model Research Report

Generated: [date]

## Editorial Overview

[Opinionated analysis of the current model landscape — 3-5 paragraphs covering:
- Where things stand right now and what has shifted recently
- Which providers are leading and on what axes
- Major trends (open-source progress, pricing shifts, new entrants)
- What this means practically — what should teams be paying attention to
- Any surprises or contrarian takes from the research

This is the "so what" section. Be direct and opinionated, not just descriptive.]

## Recommended Favourites

| Model | Tier | Speed | Best For |
|-------|------|-------|----------|
| [model_id] | [tier] | [speed] | [best_for] |
| ... | ... | ... | ... |

[Rationale for each pick — why this model, what makes it stand out, and why it's ordered where it is]

## Model Profiles

[Full research profiles for each model in the deep-research shortlist (top 5-10)]

### [model_id]

**Tier:** [tier] | **Speed:** [speed] | **Context:** [context_length]
**Strengths:** [tag1, tag2, tag3]
**Weaknesses:** [tag1, tag2]
**Best for:** [one sentence]

[2-3 paragraph research summary covering:
- Key capabilities and what it excels at
- Community consensus and real-world reputation
- How it compares to alternatives
- Notable benchmarks or achievements
- Pricing and practical considerations]

Sources: [list URLs used]

---

[Repeat for each model in the shortlist]

## The Full Landscape

[Quick summaries of ALL other notable models from the survey that didn't make the deep-research shortlist. Organize into meaningful categories that emerge naturally from the data — don't force a predetermined structure. Each model gets a 1-2 line summary with key differentiators.

Examples of categories that might emerge: provider families, capability tiers, use-case clusters, pricing tiers, open vs closed. Let the data decide.]

## Data Sources

- [List all ranking sites, leaderboards, and APIs consulted with dates]

## Methodology

[Brief description of the three-stage process, ranking criteria, and any caveats]
```

# Data File Format

Write a pipe-separated values file to `docs/models.psv`. This is the machine-readable companion to the markdown report.

Fields (in order):

1. `model` — full model ID (e.g. `gemini/gemini-3.1-pro-preview`)
2. `context` — context window in tokens
3. `tok_sec` — output tokens per second
4. `price_in` — $ per million input tokens
5. `price_out` — $ per million output tokens
6. `aa_index` — Artificial Analysis Intelligence Index (composite of 10 benchmarks across agents, coding, science, general)
7. `arena_elo` — Arena human preference Elo score
8. `swe_bench` — SWE-bench Verified % (coding)
9. `gpqa` — GPQA Diamond % (reasoning/science)
10. `favourite` — yes / no
11. `description` — free text summary (no pipes)

Rules:
- Header row first
- Sort by `aa_index` descending; models without a score go at the bottom
- Use blank for unknown values (not "N/A" or "0")
- Include ALL notable models from the survey, not just the deep-research shortlist
- Prices in USD, no $ sign in the values

Example:
```
model|context|tok_sec|price_in|price_out|aa_index|arena_elo|swe_bench|gpqa|favourite|description
gemini/gemini-3.1-pro-preview|1000000|91|2.00|12.00|53|1500|80.6|94.3|yes|Google's frontier reasoning model, #1 ARC-AGI-2, best price-to-quality ratio
openrouter/anthropic/claude-opus-4.6|200000|72|5.00|25.00|53|1503|80.8|91.3|no|#1 Arena, best coding and creative writing, 1M context in beta
```
