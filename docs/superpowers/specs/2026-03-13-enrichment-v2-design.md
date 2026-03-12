# Enrichment V2 — Fix Broken Sources + Add Release Metadata

**Date:** 2026-03-13
**Status:** Approved
**Scope:** Replace broken LiveBench and LMArena enrichment sources, extract OpenRouter metadata during discovery, surface knowledge cutoff dates

## Problem

Both enrichment sources are broken:
- **LiveBench** (`livebench/results` on HuggingFace) returns 401 — dataset went private
- **LMArena** (`chatbot-arena-leaderboard/leaderboard_table.csv`) returns 404 — space renamed, file never existed without a date suffix, and the CSV doesn't contain Elo anyway (Elo is in pickle files)

Additionally, the OpenRouter models API returns rich metadata (pricing, context length, listing date) that we currently discard.

## Data Sources

### Source 1: LMArena Arena Catalog (Elo ratings)

- **URL:** `https://raw.githubusercontent.com/lmarena/arena-catalog/main/data/leaderboard-text.json`
- **Format:** JSON — nested object. Structure: `{"full": {"model-name": {"rating": 1487.0, "rating_q975": 1493.0, "rating_q025": 1480.0}, ...}, "coding": {...}, ...}`. We read only the `full` category.
- **Coverage:** ~200 models (proprietary + open)
- **Auth:** None
- **Fields extracted:** `arena_elo` (from `full` category `rating`)

### Source 2: LMArena HF CSV (knowledge cutoff, org, license)

- **URL:** `https://huggingface.co/spaces/lmarena-ai/arena-leaderboard/resolve/main/leaderboard_table_YYYYMMDD.csv`
- **Format:** CSV with columns: `key`, `Model`, `MT-bench (score)`, `MMLU`, `Knowledge cutoff date`, `License`, `Organization`, `Link`
- **Coverage:** ~340 models
- **Auth:** None
- **Filename discovery:** Query HF API at `https://huggingface.co/api/spaces/lmarena-ai/arena-leaderboard/tree/main` (returns JSON array of file objects with `rfilename` field). Filter for entries matching `leaderboard_table_\d{8}\.csv`, extract dates, pick the latest. Timeout: 15s. Fallback filename: `leaderboard_table_20250804.csv` (last known good snapshot).
- **Fields extracted:** `knowledge_cutoff`, `organization`, `license`

### Source 3: OpenRouter `/api/v1/models` (pricing, context, listing date)

- **URL:** Already fetched during model discovery
- **Format:** JSON
- **Coverage:** All OpenRouter models
- **Auth:** None (public endpoint)
- **Fields extracted:** `context_length` (int), `pricing_in` (string, per-token), `pricing_out` (string, per-token), `openrouter_listed` (Unix timestamp)

## Model Name Matching

Arena sources use bare model names (e.g. `gemini-2.5-pro`). Our model IDs are provider-prefixed (e.g. `gemini/gemini-2.5-pro-preview`). Matching strategy:

### `_normalize_model_name(name: str) -> str`

1. Lowercase
2. Strip provider prefix (everything up to and including the last `/`)
3. Strip common suffixes in order: date patterns (`-YYYYMMDD`, `-YY-MM-DD`) first, then `-preview`, `-latest`, `-experimental`, `-exp`
4. Do NOT strip version suffixes like `-v3`, `-v3.2` — these distinguish genuinely different models
5. Normalize separators to `-`

### Normalizer test cases

| Input | Normalized |
|-------|-----------|
| `gemini/gemini-2.5-pro-preview` | `gemini-2.5-pro` |
| `openrouter/anthropic/claude-sonnet-4-20250514` | `claude-sonnet-4` |
| `openai/gpt-5.3-codex` | `gpt-5.3-codex` |
| `openrouter/deepseek/deepseek-v3.2` | `deepseek-v3.2` |
| `gemini-2.5-pro` (arena key, no prefix) | `gemini-2.5-pro` |
| `gemini/gemini-2.0-flash-thinking-exp` | `gemini-2.0-flash-thinking` |
| `openrouter/meta-llama/llama-3.1-405b-instruct` | `llama-3.1-405b-instruct` |
| `gpt-4.1-mini-latest` | `gpt-4.1-mini` |

### Matching rules

- Normalize both the arena key and the provider model ID
- Exact match on normalized form
- Apply arena data (Elo, cutoff, org, license) to ALL provider models that match the same arena key
- If no match, skip — wrong metadata is worse than missing metadata
- Log unmatched arena models at DEBUG level

### What we explicitly don't do

- No Levenshtein/fuzzy matching
- No cross-family matching
- No alias table (may add later if needed)

## OpenRouter Metadata Extraction

`_fetch_openrouter_models()` changes from returning `list[str]` to returning `tuple[list[str], dict[str, dict]]` — model IDs plus a metadata dict keyed by full model ID. The ZDR path returns `(models, {})` since the ZDR endpoint doesn't include the same metadata fields.

For each model in the OpenRouter response:

```python
{
    "context_length": m.get("context_length"),
    "pricing_in": m.get("pricing", {}).get("prompt"),
    "pricing_out": m.get("pricing", {}).get("completion"),
    "openrouter_listed": m.get("created"),
}
```

The caller (`_refresh_provider_models` or `_fetch_enrichment`) merges this into `_annotations[model_id]["metadata"]`.

### Design decisions

- **Pricing as strings** — avoid float precision issues with tiny per-token values like `"0.0000003"`
- **No cross-pollination for pricing** — OpenRouter pricing and `openrouter_listed` stay on `openrouter/*` model IDs only. Even if `openai/gpt-5.2` and `openrouter/openai/gpt-5.2` are the same underlying model, pricing is provider-specific.
- **Cross-pollination OK for arena data** — Elo, knowledge_cutoff, organization, and license apply to ALL provider models that match a given arena key (e.g. both `openai/gpt-5.2` and `openrouter/openai/gpt-5.2` get the same Elo). These are model-level facts, not provider-specific.
- **`openrouter_listed` not `release_date`** — the `created` timestamp is when OpenRouter listed the model, not when it was released. Named honestly.

## Enrichment Pipeline

Updated `_fetch_enrichment()`:

1. **Arena Elo** — GET arena-catalog JSON, parse `full` category, normalize names, match against discovered models, write `arena_elo`
2. **Arena metadata** — Discover latest CSV filename via HF API (fallback to hardcoded), GET the CSV, normalize names, match, write `knowledge_cutoff`, `organization`, `license`
3. **OpenRouter metadata** — Already captured during `_fetch_openrouter_models()`. Merged by caller before `_fetch_enrichment()` runs.

All three are fail-safe: if any source errors, log a warning and continue. Partial enrichment is fine.

## "What's New" — Date Fields

Three date-like signals, none a true release date:

| Field | Meaning | Coverage |
|-------|---------|----------|
| `first_seen` | When our server first discovered it | All models |
| `openrouter_listed` | When OpenRouter listed it | OpenRouter models only |
| `knowledge_cutoff` | Training data cutoff (e.g. `2024/2`) | ~340 models via CSV |

- `_get_recent_models()` continues to use `first_seen` (answers "what's new to you")
- `_build_instructions()` shows "Recently Added" using `first_seen` (unchanged)
- `search_models` results include `knowledge_cutoff` and `openrouter_listed` when available

No synthetic "release date" — that would be dishonest.

## Annotations Schema (Updated)

```json
{
  "openai/gpt-5.2": {
    "metadata": {
      "arena_elo": 1486,
      "knowledge_cutoff": "2025/6",
      "organization": "OpenAI",
      "license": "Proprietary",
      "first_seen": "2026-03-12T16:17:55Z",
      "last_updated": "2026-03-13T10:00:00Z"
    },
    "usage": {
      "call_count": 25,
      "last_used": "2026-03-12T00:00:00Z"
    },
    "annotations": {
      "note": "Fast frontier reasoning"
    }
  },
  "openrouter/deepseek/deepseek-v3.2": {
    "metadata": {
      "arena_elo": 1350,
      "knowledge_cutoff": "2025/3",
      "organization": "DeepSeek",
      "license": "MIT",
      "context_length": 131072,
      "pricing_in": "0.0000003",
      "pricing_out": "0.0000008",
      "openrouter_listed": 1741564800,
      "first_seen": "2026-03-12T16:17:55Z",
      "last_updated": "2026-03-13T10:00:00Z"
    },
    "usage": { "..." : "..." },
    "annotations": { "..." : "..." }
  }
}
```

Note the asymmetry: OpenRouter models have pricing/context/listed fields; direct-provider models don't. All metadata fields are optional.

## Files Changed

| File | Change |
|------|--------|
| `server.py` | Replace `_LIVEBENCH_URL` + `_LMARENA_URL` with `_ARENA_CATALOG_URL` + `_ARENA_METADATA_BASE` |
| `server.py` | Add `_normalize_model_name()` |
| `server.py` | Add `_discover_latest_arena_csv()` |
| `server.py` | Change `_fetch_openrouter_models()` return type to `tuple[list[str], dict]` |
| `server.py` | Rewrite `_parse_livebench()` → `_parse_arena_catalog()` |
| `server.py` | Rewrite `_parse_lmarena()` → `_parse_arena_metadata()` |
| `server.py` | Update `_fetch_enrichment()` pipeline |
| `server.py` | Update `search_models` to surface new fields |
| `tests/test_annotations.py` | Update/replace parser tests, add normalizer tests, add OpenRouter metadata tests |
| `CLAUDE.md` | Update enrichment source references, remove `livebench_avg` from schema example, update `search_models` description |

## Not Changing

- `_get_recent_models()`, `_build_instructions()`, `_get_favourites()`
- `annotate_models`, `refresh_models`, `completion` tool signatures
- No new dependencies — all via `urllib` + `json`/`csv` stdlib

## Removed

- `_LIVEBENCH_URL` constant
- `_LMARENA_URL` constant
- `_parse_livebench()` function
- `_parse_lmarena()` function
