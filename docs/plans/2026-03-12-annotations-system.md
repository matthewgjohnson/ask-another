# Annotations System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the PSV model catalog with a single `~/.ask-another-annotations.json` file that combines automated metadata enrichment (from providers, LiveBench, LMArena) with personal annotations (notes), and derives favourites from actual usage.

**Architecture:** The annotations file has per-model entries with two sub-objects: `metadata` (automated — provider data, benchmarks, `last_updated` timestamp) and `annotations` (user-driven — notes only). Favourites are derived from a `usage` object (`call_count`, `last_used`) — top 5 by call count. On startup (lifespan), the server checks `metadata.last_updated` against TTL; if stale, it refreshes provider models and benchmark data. The `FAVOURITES` env var and PSV file are removed entirely.

**Tech Stack:** Python, FastMCP, httpx/urllib for HuggingFace CSV fetches, JSON for persistence

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/ask_another/server.py` | All changes — single-file server |
| `src/ask_another/models.psv` | **DELETE** — replaced by annotations file |
| `docs/models.psv` | **DELETE** — no longer canonical |
| `tests/test_annotations.py` | **CREATE** — tests for annotations system |
| `tests/test_psv.py` | **DELETE** — no longer relevant |

---

## Chunk 1: Annotations File — Load, Save, and Schema

### Task 1: Define annotations file schema and load/save helpers

**Files:**
- Create: `tests/test_annotations.py`
- Modify: `src/ask_another/server.py:1-55` (new globals, dataclass removal)

The annotations file lives at `~/.ask-another-annotations.json` (configurable via `ANNOTATIONS_FILE` env var). Schema:

```json
{
  "openai/gpt-5.2": {
    "metadata": {
      "context": 200000,
      "price_in": 1.75,
      "price_out": 14.00,
      "arena_elo": 1486,
      "livebench_avg": 72.3,
      "first_seen": "2026-01-15T08:00:00Z",
      "last_updated": "2026-03-12T10:30:00Z"
    },
    "usage": {
      "call_count": 47,
      "last_used": "2026-03-12T14:20:00Z"
    },
    "annotations": {
      "note": "Fast, good for code review"
    }
  }
}
```

- [ ] **Step 1: Write failing test — load empty/missing file**

```python
# tests/test_annotations.py
"""Tests for the annotations system."""

import json
from pathlib import Path

import ask_another.server as server


def test_load_annotations_missing_file(tmp_path, monkeypatch):
    """Loading a nonexistent annotations file returns empty dict."""
    monkeypatch.setenv("ANNOTATIONS_FILE", str(tmp_path / "annotations.json"))
    result = server._load_annotations()
    assert result == {}


def test_load_annotations_existing_file(tmp_path, monkeypatch):
    """Loading an existing annotations file returns its contents."""
    ann_file = tmp_path / "annotations.json"
    data = {
        "openai/gpt-5.2": {
            "metadata": {"context": 200000, "last_updated": "2026-03-12T10:30:00Z"},
            "usage": {"call_count": 5, "last_used": "2026-03-12T14:20:00Z"},
            "annotations": {"note": "fast"},
        }
    }
    ann_file.write_text(json.dumps(data))
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))
    result = server._load_annotations()
    assert result == data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py -v`
Expected: FAIL — `_load_annotations` does not exist

- [ ] **Step 3: Implement `_load_annotations` and `_save_annotations`**

In `server.py`, add near the top (after imports, before provider registry):

```python
# In-memory annotations: {model_id: {metadata: {...}, usage: {...}, annotations: {...}}}
_annotations: dict[str, dict] = {}


def _get_annotations_path() -> Path:
    """Return the annotations file path from env or default."""
    return Path(
        os.environ.get("ANNOTATIONS_FILE", os.path.expanduser("~/.ask-another-annotations.json"))
    )


def _load_annotations() -> dict[str, dict]:
    """Load annotations from the JSON file. Returns empty dict if missing."""
    path = _get_annotations_path()
    if not path.is_file():
        logger.debug("No annotations file at %s", path)
        return {}
    try:
        data = json.loads(path.read_text())
        logger.debug("Loaded %d annotations from %s", len(data), path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load annotations from %s: %s", path, exc)
        return {}


def _save_annotations(data: dict[str, dict]) -> None:
    """Save annotations to the JSON file."""
    path = _get_annotations_path()
    path.write_text(json.dumps(data, indent=2) + "\n")
    logger.debug("Saved %d annotations to %s", len(data), path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py -v`
Expected: PASS

- [ ] **Step 5: Write failing test — save annotations**

```python
# append to tests/test_annotations.py

def test_save_annotations(tmp_path, monkeypatch):
    """Saving annotations writes valid JSON to disk."""
    ann_file = tmp_path / "annotations.json"
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))
    data = {
        "openai/gpt-5.2": {
            "metadata": {"context": 200000},
            "usage": {"call_count": 1, "last_used": "2026-03-12T00:00:00Z"},
            "annotations": {},
        }
    }
    server._save_annotations(data)
    assert ann_file.exists()
    loaded = json.loads(ann_file.read_text())
    assert loaded == data
```

- [ ] **Step 6: Run test to verify it passes** (implementation already done in step 3)

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_save_annotations -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tests/test_annotations.py src/ask_another/server.py
git commit -m "feat: add annotations file load/save helpers"
```

---

### Task 2: Usage tracking in `completion`

**Files:**
- Modify: `src/ask_another/server.py` (completion tool, ~line 587-649)
- Modify: `tests/test_annotations.py`

- [ ] **Step 1: Write failing test — completion increments call_count**

```python
# append to tests/test_annotations.py

def test_completion_tracks_usage(tmp_path, monkeypatch):
    """completion() increments call_count and updates last_used."""
    ann_file = tmp_path / "annotations.json"
    ann_file.write_text("{}")
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.delenv("FAVOURITES", raising=False)
    server._load_config()
    server._annotations = server._load_annotations()

    # Mock _resolve_model and litellm.completion
    monkeypatch.setattr(server, "_resolve_model", lambda m: ("openai/gpt-5.2", "sk-test"))
    monkeypatch.setattr(server, "_get_models", lambda provider=None, *, zdr=None: ["openai/gpt-5.2"])

    class FakeChoice:
        class message:
            content = "Hello"
    class FakeResponse:
        choices = [FakeChoice()]

    import litellm
    monkeypatch.setattr(litellm, "completion", lambda **kw: FakeResponse())

    server.completion(model="openai/gpt-5.2", prompt="hi")

    loaded = json.loads(ann_file.read_text())
    assert loaded["openai/gpt-5.2"]["usage"]["call_count"] == 1

    # Call again
    server.completion(model="openai/gpt-5.2", prompt="hi again")
    loaded = json.loads(ann_file.read_text())
    assert loaded["openai/gpt-5.2"]["usage"]["call_count"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_completion_tracks_usage -v`
Expected: FAIL — no usage tracking yet

- [ ] **Step 3: Add usage tracking to `completion`**

After the `litellm.completion()` call and before the return, add:

```python
    # Track usage
    _track_usage(full_model)
```

And add the helper:

```python
def _track_usage(model_id: str) -> None:
    """Increment call_count and update last_used for a model."""
    entry = _annotations.setdefault(model_id, {})
    usage = entry.setdefault("usage", {"call_count": 0, "last_used": ""})
    usage["call_count"] = usage.get("call_count", 0) + 1
    usage["last_used"] = datetime.now(timezone.utc).isoformat()
    _save_annotations(_annotations)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_completion_tracks_usage -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ask_another/server.py tests/test_annotations.py
git commit -m "feat: track model usage in annotations file"
```

---

### Task 3: Derive favourites from usage (top 5 by call_count)

**Files:**
- Modify: `src/ask_another/server.py` (`_build_instructions`, `_resolve_model`)
- Modify: `tests/test_annotations.py`

- [ ] **Step 1: Write failing test — top 5 favourites by usage**

```python
# append to tests/test_annotations.py

def test_get_favourites_from_usage():
    """Top 5 models by call_count are returned as favourites."""
    annotations = {
        f"openai/model-{i}": {
            "usage": {"call_count": i, "last_used": "2026-03-12T00:00:00Z"}
        }
        for i in range(1, 8)
    }
    result = server._get_favourites(annotations)
    assert len(result) == 5
    assert result[0] == "openai/model-7"  # highest count first
    assert result[4] == "openai/model-3"


def test_get_favourites_empty():
    """No usage data means no favourites."""
    result = server._get_favourites({})
    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_get_favourites_from_usage -v`
Expected: FAIL — `_get_favourites` does not exist

- [ ] **Step 3: Implement `_get_favourites` and `_get_recent_models`**

```python
def _get_favourites(annotations: dict[str, dict]) -> list[str]:
    """Derive top 5 favourite models by call_count from annotations."""
    models_with_usage = [
        (model_id, entry.get("usage", {}).get("call_count", 0))
        for model_id, entry in annotations.items()
        if entry.get("usage", {}).get("call_count", 0) > 0
    ]
    models_with_usage.sort(key=lambda x: x[1], reverse=True)
    return [model_id for model_id, _ in models_with_usage[:5]]


def _get_recent_models(annotations: dict[str, dict], days: int = 7) -> list[tuple[str, str]]:
    """Return models first seen within the last N days, newest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for model_id, entry in annotations.items():
        first_seen = entry.get("metadata", {}).get("first_seen")
        if not first_seen:
            continue
        try:
            seen_dt = datetime.fromisoformat(first_seen)
            if seen_dt >= cutoff:
                recent.append((model_id, first_seen[:10]))  # date only
        except (ValueError, TypeError):
            continue
    recent.sort(key=lambda x: x[1], reverse=True)
    return recent
```

Note: add `from datetime import timedelta` to the imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_get_favourites_from_usage tests/test_annotations.py::test_get_favourites_empty -v`
Expected: PASS

- [ ] **Step 5: Wire `_get_favourites` into `_build_instructions` and `_resolve_model`**

In `_resolve_model`, replace `_favourites` with `_get_favourites(_annotations)`:

```python
def _resolve_model(model: str) -> tuple[str, str]:
    """Resolve a model identifier or shorthand to (full_id, api_key)."""
    favourites = _get_favourites(_annotations)

    # Try shorthand resolution against favourites first
    matches = [fav for fav in favourites if fav.startswith(f"{model}/")]

    if len(matches) == 1:
        fav = matches[0]
        for provider, api_key in _provider_registry.items():
            if fav.startswith(f"{provider}/"):
                logger.debug("Resolved shorthand '%s' -> %s (provider=%s)", model, fav, provider)
                return fav, api_key

    if len(matches) > 1:
        match_list = ", ".join(matches)
        raise ValueError(
            f"Ambiguous shorthand '{model}' matches multiple favourites: {match_list}. "
            f"Use a more specific shorthand (e.g. '{_get_family(matches[0])}')"
        )

    # Full identifier: route directly
    if "/" in model:
        for provider, api_key in _provider_registry.items():
            if model.startswith(f"{provider}/"):
                logger.debug("Resolved full model ID '%s' (provider=%s)", model, provider)
                return model, api_key

    logger.warning("Model resolution failed for '%s'", model)
    fav_list = ", ".join(favourites) if favourites else "(none — use the MCP to build usage)"
    raise ValueError(
        f"No favourite matches '{model}'. Available favourites: {fav_list}"
    )
```

In `_build_instructions`, replace the favourites block (detailed code in Task 4 Step 3).

- [ ] **Step 6: Write tests — instructions ordering and shorthand resolution**

```python
def test_build_instructions_from_usage(tmp_path, monkeypatch):
    """Instructions surface top models by usage, highest call_count first."""
    monkeypatch.setenv("ANNOTATIONS_FILE", str(tmp_path / "a.json"))
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.setattr(server, "_annotations", {
        "openai/gpt-5.2": {
            "usage": {"call_count": 10, "last_used": "2026-03-12T00:00:00Z"},
            "annotations": {"note": "Fast reasoning"},
        },
        "openai/gpt-4o": {
            "usage": {"call_count": 3, "last_used": "2026-03-11T00:00:00Z"},
        },
    })
    instructions = server._build_instructions()
    # Both present
    assert "openai/gpt-5.2" in instructions
    assert "openai/gpt-4o" in instructions
    # Higher usage appears first
    assert instructions.index("openai/gpt-5.2") < instructions.index("openai/gpt-4o")


def test_resolve_model_shorthand_from_usage(monkeypatch):
    """Shorthand resolution uses usage-derived favourites."""
    monkeypatch.setattr(server, "_annotations", {
        "openai/gpt-5.2": {
            "usage": {"call_count": 10, "last_used": "2026-03-12T00:00:00Z"},
        },
    })
    monkeypatch.setattr(server, "_provider_registry", {"openai": "sk-test"})
    full_id, api_key = server._resolve_model("openai")
    assert full_id == "openai/gpt-5.2"
    assert api_key == "sk-test"
```

- [ ] **Step 7: Run all tests**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/ask_another/server.py tests/test_annotations.py
git commit -m "feat: derive favourites from usage (top 5 by call_count)"
```

---

## Chunk 2: Remove PSV System and FAVOURITES Env Var

### Task 4: Remove PSV catalog, FAVOURITES env var, and ModelMeta

**Files:**
- Modify: `src/ask_another/server.py` (remove `_load_psv`, `ModelMeta`, `_model_catalog`, `_parse_favourites`, `FAVOURITES` parsing)
- Delete: `src/ask_another/models.psv`
- Delete: `docs/models.psv`
- Delete: `tests/test_psv.py`
- Modify: `pyproject.toml` (remove PSV from build includes)

- [ ] **Step 1: Remove `ModelMeta` dataclass, `_model_catalog` global, `_load_psv` function, `_parse_favourites` function**

Remove from `server.py`:
- Lines 41-48 (`ModelMeta` dataclass)
- Line 50-51 (`_model_catalog` global)
- Lines 145-165 (`_parse_favourites`)
- Lines 168-199 (`_load_psv`)
- In `_load_config`: remove `_model_catalog = _load_psv()`, remove `_favourites` parsing, remove PSV bootstrap block (lines 254-275)
- Remove `_favourites` global (line 29)

- [ ] **Step 2: Update `_load_config` to load annotations instead**

```python
def _load_config() -> None:
    """Scan environment and populate provider registry and cache TTL."""
    global _provider_registry, _cache_ttl_minutes, _zero_data_retention, _annotations

    _configure_logging()

    _provider_registry = {}
    provider_pattern = re.compile(r"^PROVIDER_\w+$")

    for var_name, value in os.environ.items():
        if provider_pattern.match(var_name):
            provider, api_key = _parse_provider_config(var_name, value)
            _provider_registry[provider] = api_key

    ttl_str = os.environ.get("CACHE_TTL_MINUTES", "360")
    try:
        _cache_ttl_minutes = int(ttl_str)
    except ValueError:
        raise ValueError(f"Invalid CACHE_TTL_MINUTES value: {ttl_str}")

    zdr_val = os.environ.get("ZERO_DATA_RETENTION", "").lower()
    if zdr_val:
        _zero_data_retention = zdr_val in ("1", "true", "yes")
    else:
        _zero_data_retention = True

    _annotations = _load_annotations()

    logger.info(
        "Config loaded: %d providers, %d annotations, ZDR=%s, cache_ttl=%dm",
        len(_provider_registry), len(_annotations),
        _zero_data_retention, _cache_ttl_minutes,
    )
```

- [ ] **Step 3: Update `_build_instructions` to use annotations**

Replace the favourites block to use `_get_favourites(_annotations)` and show notes + call counts:

```python
def _build_instructions() -> str:
    """Build server instructions dynamically from config."""
    lines = [
        "Purpose:",
        "  - Ask another LLM for a second opinion.",
        "  - Provide access to other models through litellm.",
        "Howto:",
        "  - For a quick query, use completion with a favourite shorthand (see below).",
        "  - To find any model, use search_models — results include metadata",
        "    when available.",
        "  - For deep research tasks, use start_research. If it is interrupted or",
        "    times out, the task continues in the background — use check_research",
        "    to retrieve results later, or cancel_research to stop a running task.",
        "  - To generate images, use generate_image with a model like",
        "    openai/gpt-image-1 or gemini/gemini-2.5-flash-image.",
        "  - Never guess model IDs.",
        "Feedback:",
        "  - We'd love to hear how ask-another is working for you. Call",
        "    feedback to share issues, suggestions, or anything that felt",
        "    harder than it should be.",
        "  - Call feedback before retrying if you receive confusing output",
        "    or a tool call fails — it helps us improve.",
    ]
    favourites = _get_favourites(_annotations)
    if favourites:
        lines.append("Favourite Models:")
        for fav in favourites:
            entry = _annotations.get(fav, {})
            note = entry.get("annotations", {}).get("note", "")
            count = entry.get("usage", {}).get("call_count", 0)
            parts = [fav]
            if note:
                parts.append(note)
            parts.append(f"({count} calls)")
            lines.append(f"  - {' — '.join(parts)}")

    # Surface recently added models (first_seen within last 7 days)
    recent = _get_recent_models(_annotations, days=7)
    if recent:
        lines.append("Recently Added:")
        for model_id, first_seen in recent[:5]:
            lines.append(f"  - {model_id} (added {first_seen})")

    return "\n".join(lines)
```

- [ ] **Step 4: Update `_resolve_model` to use derived favourites**

Replace `_favourites` references with `_get_favourites(_annotations)`.

- [ ] **Step 5: Update `search_models` to use annotations for descriptions**

Replace `_model_catalog.get(m)` with reading from `_annotations`:

```python
    for m in models:
        entry = _annotations.get(m, {})
        note = entry.get("annotations", {}).get("note", "")
        meta = entry.get("metadata", {})
        # Build description from metadata fields
        desc_parts = []
        if meta.get("arena_elo"):
            desc_parts.append(f"Elo {meta['arena_elo']}")
        if meta.get("livebench_avg"):
            desc_parts.append(f"LiveBench {meta['livebench_avg']}")
        if note:
            desc_parts.append(note)
        if desc_parts:
            lines.append(f"{m} — {', '.join(desc_parts)}")
        else:
            lines.append(m)
```

- [ ] **Step 6: Migrate ZDR tests from `test_psv.py` to `tests/test_annotations.py`**

Copy `test_zero_data_retention_flag`, `test_zero_data_retention_default`, and `test_zero_data_retention_opt_out` from `tests/test_psv.py` into `tests/test_annotations.py` (they test `_load_config`, not PSV).

- [ ] **Step 7: Delete PSV files and old test**

```bash
git rm src/ask_another/models.psv
git rm docs/models.psv
git rm tests/test_psv.py
```

- [ ] **Step 8: Update `pyproject.toml` — remove PSV include**

Change:
```toml
include = ["src/ask_another/**/*.py", "src/ask_another/**/*.psv"]
```
To:
```toml
include = ["src/ask_another/**/*.py"]
```

- [ ] **Step 9: Run all tests**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: PASS (test_psv.py deleted, ZDR tests migrated, test_annotations.py passes)

- [ ] **Step 10: Commit**

```bash
git add src/ask_another/server.py tests/test_annotations.py pyproject.toml
git commit -m "refactor: remove PSV catalog and FAVOURITES env var, use annotations file"
```

---

## Chunk 3: Annotate Models Tool

### Task 5: Add `annotate_models` tool

**Files:**
- Modify: `src/ask_another/server.py`
- Modify: `tests/test_annotations.py`

- [ ] **Step 1: Write failing test**

```python
def test_annotate_models_adds_note(tmp_path, monkeypatch):
    """annotate_models writes a note to the annotations file."""
    ann_file = tmp_path / "annotations.json"
    ann_file.write_text("{}")
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))
    server._annotations = server._load_annotations()

    result = server.annotate_models(
        model="openai/gpt-5.2",
        note="Great for code review",
    )
    assert "saved" in result.lower()

    loaded = json.loads(ann_file.read_text())
    assert loaded["openai/gpt-5.2"]["annotations"]["note"] == "Great for code review"


def test_annotate_models_updates_note(tmp_path, monkeypatch):
    """annotate_models overwrites an existing note without touching other fields."""
    ann_file = tmp_path / "annotations.json"
    data = {
        "openai/gpt-5.2": {
            "metadata": {"context": 200000},
            "usage": {"call_count": 5, "last_used": "2026-03-12T00:00:00Z"},
            "annotations": {"note": "old note"},
        }
    }
    ann_file.write_text(json.dumps(data))
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))
    server._annotations = server._load_annotations()

    server.annotate_models(model="openai/gpt-5.2", note="new note")

    loaded = json.loads(ann_file.read_text())
    assert loaded["openai/gpt-5.2"]["annotations"]["note"] == "new note"
    assert loaded["openai/gpt-5.2"]["usage"]["call_count"] == 5  # untouched
    assert loaded["openai/gpt-5.2"]["metadata"]["context"] == 200000  # untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_annotate_models_adds_note -v`
Expected: FAIL — `annotate_models` does not exist

- [ ] **Step 3: Implement `annotate_models` tool**

```python
@mcp.tool()
def annotate_models(
    model: str,
    note: str,
) -> str:
    """Add or update a personal note on a model. Notes appear in search_models
    results and in the favourites list in server instructions.

    Args:
        model: Full model identifier (e.g. 'openai/gpt-5.2').
        note: Your note about this model. Overwrites any existing note.
    """
    entry = _annotations.setdefault(model, {})
    annotations = entry.setdefault("annotations", {})
    annotations["note"] = note
    _save_annotations(_annotations)
    logger.debug("Annotation saved for %s", model)
    return f"Note saved for {model}."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ask_another/server.py tests/test_annotations.py
git commit -m "feat: add annotate_models tool for personal notes"
```

---

## Chunk 4: Startup Enrichment and refresh_models Tool

### Task 6: Fetch and cache all provider models on startup

**Files:**
- Modify: `src/ask_another/server.py` (lifespan)
- Modify: `tests/test_annotations.py`

- [ ] **Step 1: Write failing test — startup populates model cache**

```python
def test_startup_enrichment_populates_cache(tmp_path, monkeypatch):
    """When annotations are stale, startup refreshes provider models."""
    ann_file = tmp_path / "annotations.json"
    ann_file.write_text("{}")
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.setenv("CACHE_TTL_MINUTES", "360")

    # Mock _fetch_models to return known models
    monkeypatch.setattr(
        server, "_fetch_models",
        lambda provider, api_key, *, zdr=False: ["openai/gpt-5.2", "openai/gpt-4o"],
    )

    server._load_config()
    server._refresh_provider_models()

    # Models should be in cache
    assert "openai/gpt-5.2" in [m for models, _ in server._model_cache.values() for m in models]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_startup_enrichment_populates_cache -v`
Expected: FAIL — `_refresh_provider_models` does not exist

- [ ] **Step 3: Implement `_refresh_provider_models`**

```python
def _refresh_provider_models() -> None:
    """Scan all configured providers and populate the model cache."""
    for provider, api_key in _provider_registry.items():
        effective_zdr = _zero_data_retention
        cache_key = f"{provider}:zdr={effective_zdr}" if provider == "openrouter" else provider
        try:
            models = _fetch_models(provider, api_key, zdr=effective_zdr)
            if models:
                _model_cache[cache_key] = (models, time.time())
                logger.info("Cached %d models for %s", len(models), provider)
        except Exception as exc:
            logger.warning("Failed to refresh models for %s: %s", provider, exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_startup_enrichment_populates_cache -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ask_another/server.py tests/test_annotations.py
git commit -m "feat: add _refresh_provider_models for startup cache population"
```

---

### Task 7: Fetch LiveBench and LMArena data

**Files:**
- Modify: `src/ask_another/server.py`
- Modify: `tests/test_annotations.py`

- [ ] **Step 1: Write failing test — LiveBench CSV parsing**

```python
def test_parse_livebench_csv():
    """LiveBench CSV rows are parsed into per-model scores."""
    csv_content = (
        "model,reasoning,coding,math,language,data_analysis,global_avg\n"
        "gpt-5.2,80.1,75.3,90.2,85.0,78.4,81.8\n"
        "claude-opus-4.6,82.0,78.1,88.5,86.2,80.1,83.0\n"
    )
    result = server._parse_livebench(csv_content)
    assert "gpt-5.2" in result
    assert result["gpt-5.2"]["global_avg"] == 81.8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_parse_livebench_csv -v`
Expected: FAIL — `_parse_livebench` does not exist

- [ ] **Step 3: Implement `_parse_livebench` and `_parse_lmarena`**

```python
import csv
import io


def _parse_livebench(csv_text: str) -> dict[str, dict]:
    """Parse LiveBench CSV into {model_name: {field: value}}."""
    result = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        model = row.get("model", "").strip()
        if not model:
            continue
        scores = {}
        for key, val in row.items():
            if key == "model":
                continue
            try:
                scores[key] = float(val)
            except (ValueError, TypeError):
                pass
        if scores:
            result[model] = scores
    return result


def _parse_lmarena(csv_text: str) -> dict[str, dict]:
    """Parse LMArena leaderboard CSV into {model_name: {elo: score}}."""
    result = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        model = row.get("model", row.get("Model", "")).strip()
        elo = row.get("elo", row.get("Arena Elo", row.get("rating", "")))
        if model and elo:
            try:
                result[model] = {"arena_elo": float(elo)}
            except (ValueError, TypeError):
                pass
    return result
```

Note: The exact CSV column names will need verification against the real data. The parser is intentionally flexible — it tries multiple column name variants.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_parse_livebench_csv -v`
Expected: PASS

- [ ] **Step 5: Write failing test — LMArena CSV parsing**

```python
def test_parse_lmarena_csv():
    """LMArena CSV rows are parsed into per-model Elo scores."""
    csv_content = (
        "model,elo,votes\n"
        "gpt-5.2,1486,50000\n"
        "claude-opus-4.6,1503,45000\n"
    )
    result = server._parse_lmarena(csv_content)
    assert "gpt-5.2" in result
    assert result["gpt-5.2"]["arena_elo"] == 1486.0
```

- [ ] **Step 6: Run test to verify it passes** (implementation already done)

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_parse_lmarena_csv -v`
Expected: PASS

- [ ] **Step 7: Implement `_fetch_enrichment` to download CSVs and merge into annotations**

```python
_LIVEBENCH_URL = "https://huggingface.co/datasets/livebench/results/resolve/main/all_groups.csv"
_LMARENA_URL = "https://huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard/resolve/main/leaderboard_table.csv"


def _fetch_enrichment() -> None:
    """Fetch LiveBench and LMArena data, merge into annotations metadata."""
    now = datetime.now(timezone.utc).isoformat()

    # Fetch LiveBench
    try:
        req = urllib.request.Request(_LIVEBENCH_URL)
        with urllib.request.urlopen(req, timeout=30) as resp:
            livebench = _parse_livebench(resp.read().decode())
        logger.info("Fetched LiveBench data for %d models", len(livebench))
    except Exception as exc:
        logger.warning("Failed to fetch LiveBench: %s", exc)
        livebench = {}

    # Fetch LMArena
    try:
        req = urllib.request.Request(_LMARENA_URL)
        with urllib.request.urlopen(req, timeout=30) as resp:
            lmarena = _parse_lmarena(resp.read().decode())
        logger.info("Fetched LMArena data for %d models", len(lmarena))
    except Exception as exc:
        logger.warning("Failed to fetch LMArena: %s", exc)
        lmarena = {}

    # Merge into annotations — match by model name suffix
    all_cached_models = [m for models, _ in _model_cache.values() for m in models]
    for model_id in all_cached_models:
        entry = _annotations.setdefault(model_id, {})
        metadata = entry.setdefault("metadata", {})

        # Stamp first_seen only for newly discovered models
        if "first_seen" not in metadata:
            metadata["first_seen"] = now

        # Try to match LiveBench/LMArena by model name (last segment)
        model_name = model_id.rsplit("/", 1)[-1]
        if model_name in livebench:
            metadata["livebench_avg"] = livebench[model_name].get("global_avg")
        if model_name in lmarena:
            metadata["arena_elo"] = lmarena[model_name].get("arena_elo")

        metadata["last_updated"] = now

    _save_annotations(_annotations)
```

- [ ] **Step 8: Commit**

```bash
git add src/ask_another/server.py tests/test_annotations.py
git commit -m "feat: add LiveBench and LMArena CSV parsing and enrichment"
```

---

### Task 8: Wire enrichment into lifespan and add `refresh_models` tool

**Files:**
- Modify: `src/ask_another/server.py` (lifespan, new tool)
- Modify: `tests/test_annotations.py`

- [ ] **Step 1: Write failing test — `_needs_refresh` checks TTL**

```python
def test_needs_refresh_no_annotations():
    """Empty annotations means refresh is needed."""
    assert server._needs_refresh({}) is True


def test_needs_refresh_stale(monkeypatch):
    """Annotations older than TTL need refresh."""
    monkeypatch.setattr(server, "_cache_ttl_minutes", 1)  # 1 minute
    annotations = {
        "openai/gpt-5.2": {
            "metadata": {"last_updated": "2020-01-01T00:00:00Z"}
        }
    }
    assert server._needs_refresh(annotations) is True


def test_needs_refresh_fresh(monkeypatch):
    """Recent annotations don't need refresh."""
    monkeypatch.setattr(server, "_cache_ttl_minutes", 99999)
    annotations = {
        "openai/gpt-5.2": {
            "metadata": {"last_updated": datetime.now(timezone.utc).isoformat()}
        }
    }
    assert server._needs_refresh(annotations) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_needs_refresh_no_annotations -v`
Expected: FAIL — `_needs_refresh` does not exist

- [ ] **Step 3: Implement `_needs_refresh`**

```python
def _needs_refresh(annotations: dict[str, dict]) -> bool:
    """Check if any model metadata is stale or missing."""
    if not annotations:
        return True
    now = datetime.now(timezone.utc)
    for entry in annotations.values():
        last = entry.get("metadata", {}).get("last_updated")
        if not last:
            return True
        try:
            updated_at = datetime.fromisoformat(last)
            if (now - updated_at).total_seconds() > _cache_ttl_minutes * 60:
                return True
        except (ValueError, TypeError):
            return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py -k needs_refresh -v`
Expected: PASS

- [ ] **Step 5: Update lifespan to run enrichment**

```python
@asynccontextmanager
async def _lifespan(server: FastMCP) -> Any:
    """Lifespan context: populate caches and enrich on startup."""
    async with anyio.create_task_group() as tg:
        # Startup enrichment (run in thread to not block)
        if _needs_refresh(_annotations):
            await anyio.to_thread.run_sync(_startup_enrich)
        yield {"job_store": JobStore(tg)}


def _startup_enrich() -> None:
    """Refresh provider models and fetch benchmark data."""
    _refresh_provider_models()
    _fetch_enrichment()
    logger.info("Startup enrichment complete")
```

- [ ] **Step 6: Add `refresh_models` tool**

```python
@mcp.tool()
def refresh_models() -> str:
    """Force a re-scan of all configured providers and re-fetch benchmark
    data from LiveBench and LMArena. Use this if model data seems stale
    or after adding a new provider.
    """
    _refresh_provider_models()
    _fetch_enrichment()
    cached_count = sum(len(models) for models, _ in _model_cache.values())
    return f"Refreshed {cached_count} models across {len(_provider_registry)} providers."
```

- [ ] **Step 7: Run all tests**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/ask_another/server.py tests/test_annotations.py
git commit -m "feat: add startup enrichment and refresh_models tool"
```

---

## Chunk 5: Update CLAUDE.md and Clean Up

### Task 9: Update documentation and final cleanup

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

Replace references to PSV catalog, `FAVOURITES` env var, and `MODELS_PSV` env var. Document:
- `ANNOTATIONS_FILE` env var (default `~/.ask-another-annotations.json`)
- The annotations file schema
- How favourites are derived from usage
- `annotate_models` and `refresh_models` tools
- Startup enrichment behaviour
- LiveBench and LMArena as data sources

- [ ] **Step 2: Remove `MODELS_PSV` and `FAVOURITES` from CLAUDE.md env var docs**

- [ ] **Step 3: Run full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for annotations system"
```

---

## Chunk 6: Acceptance Tests — Subagent with Zero Context

These tests simulate a fresh user interacting with ask-another through an LLM that has no prior context — only the MCP server instructions and tools. Each test is a subagent launched with a single user prompt. The subagent has access to the ask-another MCP tools and nothing else.

**Pre-seeded annotations for tests:** Before running, write a `~/.ask-another-annotations.json` with usage data so favourites exist:

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

Each test is run as a **serial subagent** — one prompt at a time, with the subagent retaining context across prompts within the same session. This simulates a real conversation.

### Task 10: Acceptance test suite

- [ ] **Test 1: Discovery — "I just installed ask-another. What models do I have access to?"**

Launch subagent with prompt. Verify:
- Calls `search_families` or `search_models`
- Returns a meaningful list of providers/models
- Does NOT call `completion` (this is an exploration request, not a generation request)

- [ ] **Test 2: Annotate — "I find DeepSeek gives the best creative writing results. Can you note that down?"**

Continue subagent. Verify:
- Calls `annotate_models` with model matching `deepseek` and a note about creative writing
- Confirms the note was saved

- [ ] **Test 3: Annotate — "Actually, Gemini 3.1 Pro is my go-to for complex math problems. Note that too."**

Continue subagent. Verify:
- Calls `annotate_models` with model matching `gemini-3.1-pro` and a note about math
- Does NOT overwrite the DeepSeek annotation from Test 2

- [ ] **Test 4: Annotate — "And GPT-5.3-codex is the one I want for all code tasks."**

Continue subagent. Verify:
- Calls `annotate_models` with model matching `gpt-5.3-codex` and a note about code

- [ ] **Test 5: Annotation-guided completion (code) — "I'm writing a Python function that retries HTTP requests with exponential backoff. Can you ask another model if there's a cleaner way to handle the jitter?"**

Continue subagent. Verify:
- Calls `completion`
- Picks `openai/gpt-5.3-codex` (or another coding model) — guided by annotation from Test 4
- Returns a substantive answer about jitter/backoff

- [ ] **Test 6: Annotation-guided completion (creative) — "Can you rewrite this paragraph to be more vivid and engaging: 'The sun set over the mountains as the hikers returned to camp.'"**

Continue subagent. Verify:
- Calls `completion`
- Picks `openrouter/deepseek/deepseek-v3.2` — guided by the creative writing annotation from Test 2
- Returns a rewritten paragraph

- [ ] **Test 7: Annotation-guided completion (math) — "What's the integral of x²·sin(x) from 0 to π?"**

Continue subagent. Verify:
- Calls `completion`
- Picks `gemini/gemini-3.1-pro-preview` — guided by the math annotation from Test 3
- Returns a correct mathematical result

- [ ] **Test 8: General knowledge (no specific annotation) — "I think climate change is caused by solar cycles, not CO2. Ask another model if I'm right."**

Continue subagent. Verify:
- Calls `completion`
- Picks a reasonable general-purpose model from favourites (likely `openai/gpt-5.2` as highest usage)
- Returns a factual response

- [ ] **Test 9: Second opinion (vague request) — "I asked Claude about the best way to structure a monorepo and I'm not sure the answer is right. Can you get a second opinion?"**

Continue subagent. Verify:
- Calls `completion` with a sensible reformulation of the question
- Picks from favourites — any reasonable choice is acceptable
- Returns a substantive answer about monorepo structure

- [ ] **Test 10: Deep research — "I'm writing a blog post and need to understand the current state of WebAssembly support in Python. Can you research this?"**

Continue subagent. Verify:
- Calls `start_research` (NOT `completion`) — recognises this is a research task
- Picks an appropriate research model (e.g. `openrouter/perplexity/sonar-deep-research`)
- Returns research results or a job handle

- [ ] **Test 11: Image generation — "I need a logo for my side project — it's a CLI tool called 'driftwood' that converts log files into timelines. Can you generate something?"**

Continue subagent. Verify:
- Calls `generate_image` (NOT `completion`)
- Picks an image model (e.g. `openai/gpt-image-1`)
- Returns an image

- [ ] **Test 12: Refresh — "I think Google just released a new Gemini — can you check?"**

Continue subagent. Verify:
- Calls `refresh_models` to re-scan providers
- Then calls `search_models` with a gemini filter
- Reports what Gemini models are available

- [ ] **Test 13: Graceful failure — "Ask Grok to review my approach to error handling in this retry function."**

Continue subagent. Verify:
- Attempts to find Grok/xAI models via `search_models` or direct resolution
- Discovers Grok is not available in configured providers
- Tells the user Grok is not available and suggests alternatives
- Does NOT hallucinate a call to a nonexistent model

### Evaluation criteria

For each test, assess:

| Criterion | Pass | Fail |
|-----------|------|------|
| **Right tool** | Called the expected tool type | Called wrong tool (e.g. `completion` for research) |
| **Right model** | Picked a model consistent with annotations/context | Random pick or hallucinated model ID |
| **Annotation influence** | Tests 5-7 show clear annotation-guided selection | Ignored annotations, picked unrelated model |
| **Graceful degradation** | Test 13: informed user, suggested alternatives | Crashed, hallucinated, or silently failed |
| **No hallucination** | Used real model IDs verified via search | Guessed model IDs without searching |

### Running the tests

Each test is run by continuing the same subagent session (serial prompts). After all 13 prompts, produce a results table:

```markdown
| # | Prompt (short) | Expected tool | Actual tool | Expected model | Actual model | Pass? |
|---|---------------|---------------|-------------|----------------|--------------|-------|
| 1 | What models? | search_* | | | | |
| 2 | Note DeepSeek creative | annotate_models | | deepseek | | |
| ... | ... | ... | ... | ... | ... | ... |
```

- [ ] **Step 1: Back up existing annotations file**
- [ ] **Step 2: Write pre-seeded annotations**
- [ ] **Step 3: Run subagent session with all 13 prompts sequentially**
- [ ] **Step 4: Produce results table**
- [ ] **Step 5: Restore original annotations file**
- [ ] **Step 6: Commit test results to `docs/superpowers/acceptance-test-results.md`**

```bash
git add docs/superpowers/acceptance-test-results.md
git commit -m "test: acceptance test results for annotations system"
```
