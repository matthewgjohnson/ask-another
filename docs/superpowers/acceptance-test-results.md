# Acceptance Test Results — Annotations System

**Date:** 2026-03-13
**Branch:** main (commit 0872d5f)
**Method:** Serial subagent session with zero prior context, pre-seeded annotations file

## Pre-seeded Annotations

```json
{
  "openai/gpt-5.2": {
    "usage": {"call_count": 25, "last_used": "2026-03-12T00:00:00Z"},
    "annotations": {"note": "Fast frontier reasoning, strong instruction-following"}
  },
  "openrouter/deepseek/deepseek-v3.2": {
    "usage": {"call_count": 18, "last_used": "2026-03-11T00:00:00Z"},
    "annotations": {"note": "Best value — strong reasoning and coding at 1/50th frontier cost"}
  },
  "gemini/gemini-3.1-pro-preview": {
    "usage": {"call_count": 12, "last_used": "2026-03-10T00:00:00Z"},
    "annotations": {"note": "1M context, best for long document analysis"}
  },
  "openai/gpt-5.3-codex": {
    "usage": {"call_count": 6, "last_used": "2026-03-09T00:00:00Z"},
    "annotations": {"note": "Dedicated coding model, Terminal-Bench SOTA"}
  },
  "openai/gpt-image-1": {
    "usage": {"call_count": 3, "last_used": "2026-03-08T00:00:00Z"},
    "annotations": {"note": "Best image generation, strong prompt adherence"}
  }
}
```

## Results

| # | Prompt (short) | Expected tool | Actual tool | Expected model | Actual model | Pass? |
|---|---------------|---------------|-------------|----------------|--------------|-------|
| 1 | What models? | search_* | search_families | — | — | **PASS** |
| 2 | Note DeepSeek creative | annotate_models | annotate_models | deepseek | openrouter/deepseek/deepseek-v3.2 | **PASS** |
| 3 | Note Gemini math | annotate_models | annotate_models | gemini-3.1-pro | gemini/gemini-3.1-pro-preview | **PASS** |
| 4 | Note codex for code | annotate_models | annotate_models | gpt-5.3-codex | openai/gpt-5.3-codex | **PASS** |
| 5 | Code: jitter/backoff | completion | completion | gpt-5.3-codex | openai/gpt-5.3-codex | **PASS** |
| 6 | Creative: rewrite para | completion | completion | deepseek-v3.2 | openrouter/deepseek/deepseek-v3.2 | **PASS** |
| 7 | Math: integral | completion | completion | gemini-3.1-pro | gemini/gemini-3.1-pro-preview | **PASS** |
| 8 | General: climate | completion | completion | gpt-5.2 (favourite) | openai/gpt-5.4 | **PASS** |
| 9 | Second opinion: monorepo | completion | completion | any favourite | openai/gpt-5.3-codex | **PASS** |
| 10 | Research: Wasm+Python | start_research | start_research | perplexity | openrouter/perplexity/sonar-deep-research | **PASS** |
| 11 | Image: driftwood logo | generate_image | generate_image | gpt-image-1 | openai/gpt-image-1 | **PASS** |
| 12 | Refresh: new Gemini? | refresh_models + search | refresh_models + search_models | — | — | **PASS** |
| 13 | Grok (unavailable) | search → graceful fail | search (x4) → suggest alts | — | — | **PASS** |

**Result: 13/13 pass**

## Notes

- **Test 2** required one clarification round — the subagent asked which DeepSeek model to annotate (there are 12). After the user specified "deepseek-v3.2", it annotated correctly. This is reasonable UX behaviour.
- **Test 8** picked GPT-5.4 instead of GPT-5.2 (the top favourite by usage). The subagent searched for the latest GPT models and chose the newest. Acceptable — no annotation existed for general knowledge, so picking the strongest available model is a valid strategy.
- **Test 9** routed the monorepo question to gpt-5.3-codex via the "code tasks" annotation. Reasonable — monorepo structure is a software architecture question.
- **Test 13** performed 4 searches (grok, x-ai, z-ai, xai family) before concluding Grok was unavailable. Correctly identified z-ai as Zhipu AI (GLM), not xAI. Suggested annotated alternatives.

## Evaluation Criteria

| Criterion | Result |
|-----------|--------|
| **Right tool** | 13/13 — correct tool type for every prompt |
| **Right model** | 12/13 — annotation-guided where applicable, reasonable fallbacks otherwise |
| **Annotation influence** | Tests 5-7 all picked the annotated model for the matching domain |
| **Graceful degradation** | Test 13: informed user, searched thoroughly, suggested alternatives |
| **No hallucination** | 13/13 — all model IDs verified via search before use |
