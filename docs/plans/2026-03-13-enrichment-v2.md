# Enrichment V2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace two broken enrichment sources (LiveBench, LMArena CSV) with three working ones (arena-catalog JSON, arena HF CSV, OpenRouter metadata), add model name normalizer, and surface knowledge cutoff dates.

**Architecture:** New `_normalize_model_name()` enables matching bare arena names to provider-prefixed IDs. `_fetch_openrouter_models()` returns metadata alongside model IDs. `_fetch_enrichment()` is rewritten with three fail-safe data sources. All changes in `server.py` + `tests/test_annotations.py`.

**Tech Stack:** Python, urllib, json, csv (stdlib only — no new dependencies)

**Spec:** `docs/superpowers/specs/2026-03-13-enrichment-v2-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/ask_another/server.py` | All implementation changes (single-file server) |
| `tests/test_annotations.py` | All test changes (update existing + add new) |
| `CLAUDE.md` | Update enrichment docs |

---

## Chunk 1: Model Name Normalizer

### Task 1: `_normalize_model_name()` — tests and implementation

**Files:**
- Modify: `tests/test_annotations.py` (add new tests)
- Modify: `src/ask_another/server.py:437-439` (add new function before enrichment section)

- [ ] **Step 1: Write the normalizer tests**

Add to `tests/test_annotations.py`:

```python
import pytest

@pytest.mark.parametrize("input_name,expected", [
    ("gemini/gemini-2.5-pro-preview", "gemini-2.5-pro"),
    ("openrouter/anthropic/claude-sonnet-4-20250514", "claude-sonnet-4"),
    ("openai/gpt-5.3-codex", "gpt-5.3-codex"),
    ("openrouter/deepseek/deepseek-v3.2", "deepseek-v3.2"),
    ("gemini-2.5-pro", "gemini-2.5-pro"),
    ("gemini/gemini-2.0-flash-thinking-exp", "gemini-2.0-flash-thinking"),
    ("openrouter/meta-llama/llama-3.1-405b-instruct", "llama-3.1-405b-instruct"),
    ("gpt-4.1-mini-latest", "gpt-4.1-mini"),
    ("openai/gpt-5.2", "gpt-5.2"),
    ("model-preview-20250514", "model"),
])
def test_normalize_model_name(input_name, expected):
    assert server._normalize_model_name(input_name) == expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_normalize_model_name -v`
Expected: FAIL with `AttributeError: module has no attribute '_normalize_model_name'`

- [ ] **Step 3: Implement `_normalize_model_name()`**

Add to `src/ask_another/server.py` just before line 438 (`_LIVEBENCH_URL`), in the enrichment section:

```python
# Regex for date suffixes: -YYYYMMDD or -YY-MM-DD
_DATE_SUFFIX_RE = re.compile(r"-\d{4}-?\d{2}-?\d{2}$")
# Suffixes to strip (order matters: dates first, then these)
_STRIP_SUFFIXES = ("-preview", "-latest", "-experimental", "-exp")


def _normalize_model_name(name: str) -> str:
    """Normalize a model name for matching arena keys to provider IDs.

    Strips provider prefix, date suffixes, and common suffixes like -preview.
    Does NOT strip version suffixes like -v3 or -v3.2.
    """
    # Lowercase
    name = name.lower()
    # Strip provider prefix (everything up to last /)
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    # Strip date suffixes first
    name = _DATE_SUFFIX_RE.sub("", name)
    # Strip known suffixes
    for suffix in _STRIP_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break  # Only strip one suffix
    return name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_normalize_model_name -v`
Expected: PASS (all 10 parametrized cases)

- [ ] **Step 5: Commit**

```bash
git add tests/test_annotations.py src/ask_another/server.py
git commit -m "feat: add _normalize_model_name for arena-to-provider matching"
```

---

## Chunk 2: OpenRouter Metadata Extraction

### Task 2: Change `_fetch_openrouter_models()` return type

**Files:**
- Modify: `tests/test_annotations.py` (add new test)
- Modify: `src/ask_another/server.py:319-354` (`_fetch_openrouter_models`)
- Modify: `src/ask_another/server.py:357-360` (`_fetch_models`)
- Modify: `src/ask_another/server.py:413-424` (`_refresh_provider_models`)

- [ ] **Step 1: Write the test for OpenRouter metadata extraction**

Add to `tests/test_annotations.py`:

```python
def test_fetch_openrouter_models_returns_metadata(monkeypatch):
    """_fetch_openrouter_models returns model IDs and metadata dict."""
    import urllib.request

    fake_response_data = json.dumps({
        "data": [
            {
                "id": "deepseek/deepseek-v3.2",
                "context_length": 131072,
                "pricing": {"prompt": "0.0000003", "completion": "0.0000008"},
                "created": 1741564800,
            },
            {
                "id": "openai/gpt-5.2",
                "context_length": 200000,
                "pricing": {"prompt": "0.000002", "completion": "0.000008"},
                "created": 1740000000,
            },
        ]
    })

    class FakeResponse:
        def __init__(self, data):
            self._data = data.encode()
        def read(self):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    def mock_urlopen(req, timeout=None):
        return FakeResponse(fake_response_data)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    models, metadata = server._fetch_openrouter_models("fake-key")
    assert "openrouter/deepseek/deepseek-v3.2" in models
    assert "openrouter/openai/gpt-5.2" in models

    meta = metadata["openrouter/deepseek/deepseek-v3.2"]
    assert meta["context_length"] == 131072
    assert meta["pricing_in"] == "0.0000003"
    assert meta["pricing_out"] == "0.0000008"
    assert meta["openrouter_listed"] == 1741564800


def test_fetch_openrouter_models_zdr_returns_empty_metadata(monkeypatch):
    """ZDR path returns (models, {}) since ZDR endpoint lacks metadata."""
    import urllib.request

    fake_response_data = json.dumps({
        "data": [
            {"model_id": "deepseek/deepseek-v3.2"},
        ]
    })

    class FakeResponse:
        def __init__(self, data):
            self._data = data.encode()
        def read(self):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    def mock_urlopen(req, timeout=None):
        return FakeResponse(fake_response_data)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    models, metadata = server._fetch_openrouter_models("fake-key", zdr=True)
    assert "openrouter/deepseek/deepseek-v3.2" in models
    assert metadata == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_fetch_openrouter_models_returns_metadata tests/test_annotations.py::test_fetch_openrouter_models_zdr_returns_empty_metadata -v`
Expected: FAIL (return value is list, not tuple)

- [ ] **Step 3: Update `_fetch_openrouter_models()` to return metadata**

In `src/ask_another/server.py`, change `_fetch_openrouter_models` (lines 319-354):

```python
def _fetch_openrouter_models(
    api_key: str, *, zdr: bool = False
) -> tuple[list[str], dict[str, dict]]:
    """Fetch models from OpenRouter's API directly.

    Returns (model_ids, metadata_dict). When zdr is True, fetches from the
    ZDR endpoint which returns only ZDR-compatible models; metadata_dict
    is empty since the ZDR endpoint lacks per-model metadata.
    """
    if zdr:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/endpoints/zdr",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        seen: set[str] = set()
        models: list[str] = []
        for endpoint in data.get("data", []):
            model_id = endpoint.get("model_id", "")
            if model_id and model_id not in seen:
                seen.add(model_id)
                models.append(f"openrouter/{model_id}")
        logger.debug("OpenRouter ZDR endpoint returned %d models", len(models))
        return models, {}

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())

    models = []
    metadata: dict[str, dict] = {}
    for m in data.get("data", []):
        model_id = f"openrouter/{m['id']}"
        models.append(model_id)
        pricing = m.get("pricing") or {}
        metadata[model_id] = {
            "context_length": m.get("context_length"),
            "pricing_in": pricing.get("prompt"),
            "pricing_out": pricing.get("completion"),
            "openrouter_listed": m.get("created"),
        }
    logger.debug("OpenRouter models endpoint returned %d models", len(models))
    return models, metadata
```

- [ ] **Step 4: Update callers to unpack the tuple**

In `_fetch_models` (line 359-360), change:
```python
    if provider == "openrouter":
        return _fetch_openrouter_models(api_key, zdr=zdr)
```
to:
```python
    if provider == "openrouter":
        models, _ = _fetch_openrouter_models(api_key, zdr=zdr)
        return models
```

In `_refresh_provider_models` (lines 413-424), change the openrouter case to also capture metadata. Replace the function:

```python
def _refresh_provider_models() -> None:
    """Scan all configured providers and populate the model cache."""
    for provider, api_key in _provider_registry.items():
        effective_zdr = _zero_data_retention
        cache_key = f"{provider}:zdr={effective_zdr}" if provider == "openrouter" else provider
        try:
            if provider == "openrouter":
                models, or_metadata = _fetch_openrouter_models(api_key, zdr=effective_zdr)
                # Merge OpenRouter metadata into annotations
                for model_id, meta in or_metadata.items():
                    entry = _annotations.setdefault(model_id, {})
                    entry.setdefault("metadata", {}).update(meta)
            else:
                models = _fetch_models(provider, api_key, zdr=effective_zdr)
            if models:
                _model_cache[cache_key] = (models, time.time())
                logger.info("Cached %d models for %s", len(models), provider)
        except Exception as exc:
            logger.warning("Failed to refresh models for %s: %s", provider, exc)
```

- [ ] **Step 5: Run all tests to verify nothing broke**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All tests PASS (including the two new ones)

- [ ] **Step 6: Commit**

```bash
git add tests/test_annotations.py src/ask_another/server.py
git commit -m "feat: extract OpenRouter metadata during model discovery"
```

---

## Chunk 3: New Enrichment Parsers + Pipeline

### Task 3: Replace parsers and `_fetch_enrichment()`

**Files:**
- Modify: `tests/test_annotations.py` (replace parser tests, update enrichment test)
- Modify: `src/ask_another/server.py:438-521` (replace constants, parsers, and enrichment function)

- [ ] **Step 1: Write tests for new parsers**

Replace `test_parse_livebench_csv` and `test_parse_lmarena_csv` in `tests/test_annotations.py` with:

```python
def test_parse_arena_catalog():
    """Arena catalog JSON is parsed into {normalized_name: elo}."""
    catalog_json = json.dumps({
        "full": {
            "gpt-5.2": {"rating": 1486.0, "rating_q975": 1493.0, "rating_q025": 1480.0},
            "claude-opus-4.6": {"rating": 1503.0, "rating_q975": 1510.0, "rating_q025": 1496.0},
        },
        "coding": {
            "gpt-5.2": {"rating": 1490.0, "rating_q975": 1500.0, "rating_q025": 1480.0},
        },
    })
    result = server._parse_arena_catalog(catalog_json)
    assert result["gpt-5.2"] == 1486.0
    assert result["claude-opus-4.6"] == 1503.0
    assert len(result) == 2  # only 'full' category


def test_parse_arena_catalog_missing_full():
    """Returns empty dict if 'full' category is missing."""
    result = server._parse_arena_catalog(json.dumps({"coding": {}}))
    assert result == {}


def test_parse_arena_metadata():
    """Arena metadata CSV is parsed into {normalized_name: {fields}}."""
    csv_content = (
        "key,Model,MT-bench (score),MMLU,Knowledge cutoff date,License,Organization,Link\n"
        "gpt-5.2,GPT-5.2,9.1,90.5,2025/6,Proprietary,OpenAI,https://openai.com\n"
        "claude-opus-4.6,Claude Opus 4.6,9.3,91.2,2025/4,Proprietary,Anthropic,https://anthropic.com\n"
    )
    result = server._parse_arena_metadata(csv_content)
    assert "gpt-5.2" in result
    assert result["gpt-5.2"]["knowledge_cutoff"] == "2025/6"
    assert result["gpt-5.2"]["organization"] == "OpenAI"
    assert result["gpt-5.2"]["license"] == "Proprietary"
    assert "claude-opus-4.6" in result


def test_parse_arena_metadata_skips_empty_cutoff():
    """Rows with '-' or empty cutoff date are included but with None cutoff."""
    csv_content = (
        "key,Model,MT-bench (score),MMLU,Knowledge cutoff date,License,Organization,Link\n"
        "model-a,Model A,8.0,80.0,-,MIT,OrgA,http://a.com\n"
    )
    result = server._parse_arena_metadata(csv_content)
    assert result["model-a"]["knowledge_cutoff"] is None


def test_discover_latest_arena_csv(monkeypatch):
    """_discover_latest_arena_csv picks the latest dated filename."""
    import urllib.request

    file_listing = json.dumps([
        {"rfilename": "leaderboard_table_20250101.csv"},
        {"rfilename": "leaderboard_table_20250804.csv"},
        {"rfilename": "leaderboard_table_20250601.csv"},
        {"rfilename": "README.md"},
        {"rfilename": "elo_results_20250804.pkl"},
    ])

    class FakeResponse:
        def __init__(self, data):
            self._data = data.encode()
        def read(self):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    def mock_urlopen(req, timeout=None):
        return FakeResponse(file_listing)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = server._discover_latest_arena_csv()
    assert result == "leaderboard_table_20250804.csv"


def test_discover_latest_arena_csv_fallback(monkeypatch):
    """Falls back to hardcoded filename on API error."""
    import urllib.request
    import urllib.error

    def mock_urlopen(req, timeout=None):
        raise urllib.error.URLError("network error")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = server._discover_latest_arena_csv()
    assert result == "leaderboard_table_20250804.csv"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_parse_arena_catalog tests/test_annotations.py::test_parse_arena_metadata tests/test_annotations.py::test_discover_latest_arena_csv -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: Implement new parsers and discovery function**

In `src/ask_another/server.py`, replace lines 438-475 (the old constants and parsers) with:

```python
_ARENA_CATALOG_URL = (
    "https://raw.githubusercontent.com/lmarena/arena-catalog/main/data/leaderboard-text.json"
)
_ARENA_METADATA_BASE = (
    "https://huggingface.co/spaces/lmarena-ai/arena-leaderboard/resolve/main/"
)
_ARENA_METADATA_FALLBACK = "leaderboard_table_20250804.csv"
_ARENA_HF_API = (
    "https://huggingface.co/api/spaces/lmarena-ai/arena-leaderboard/tree/main"
)


def _parse_arena_catalog(json_text: str) -> dict[str, float]:
    """Parse arena-catalog JSON into {model_name: elo_rating}.

    Reads only the 'full' category. Returns normalized model names as keys.
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return {}
    full = data.get("full", {})
    result = {}
    for model_name, scores in full.items():
        rating = scores.get("rating")
        if rating is not None:
            result[_normalize_model_name(model_name)] = float(rating)
    return result


def _parse_arena_metadata(csv_text: str) -> dict[str, dict]:
    """Parse arena metadata CSV into {normalized_name: {fields}}.

    Extracts knowledge_cutoff, organization, license from each row.
    """
    result = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        key = row.get("key", "").strip()
        if not key:
            continue
        cutoff = row.get("Knowledge cutoff date", "").strip()
        result[_normalize_model_name(key)] = {
            "knowledge_cutoff": cutoff if cutoff and cutoff != "-" else None,
            "organization": row.get("Organization", "").strip() or None,
            "license": row.get("License", "").strip() or None,
        }
    return result


def _discover_latest_arena_csv() -> str:
    """Find the latest leaderboard_table_YYYYMMDD.csv in the HF space.

    Falls back to a hardcoded filename on any error.
    """
    try:
        req = urllib.request.Request(_ARENA_HF_API, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            files = json.loads(resp.read())
        pattern = re.compile(r"^leaderboard_table_(\d{8})\.csv$")
        dated = []
        for f in files:
            m = pattern.match(f.get("rfilename", ""))
            if m:
                dated.append((m.group(1), f["rfilename"]))
        if dated:
            dated.sort(reverse=True)
            logger.debug("Latest arena CSV: %s", dated[0][1])
            return dated[0][1]
    except Exception as exc:
        logger.warning("Failed to discover latest arena CSV: %s", exc)
    return _ARENA_METADATA_FALLBACK
```

- [ ] **Step 4: Run the new parser tests**

Run: `uv run --with pytest python -m pytest tests/test_annotations.py::test_parse_arena_catalog tests/test_annotations.py::test_parse_arena_catalog_missing_full tests/test_annotations.py::test_parse_arena_metadata tests/test_annotations.py::test_parse_arena_metadata_skips_empty_cutoff tests/test_annotations.py::test_discover_latest_arena_csv tests/test_annotations.py::test_discover_latest_arena_csv_fallback -v`
Expected: All PASS

- [ ] **Step 5: Rewrite `_fetch_enrichment()`**

Replace `_fetch_enrichment()` (lines 478-521) with:

```python
def _fetch_enrichment() -> None:
    """Fetch arena Elo and metadata, merge into annotations."""
    now = datetime.now(timezone.utc).isoformat()

    # --- Source 1: Arena Elo ratings ---
    arena_elo: dict[str, float] = {}
    try:
        req = urllib.request.Request(_ARENA_CATALOG_URL)
        with urllib.request.urlopen(req, timeout=30) as resp:
            arena_elo = _parse_arena_catalog(resp.read().decode())
        logger.info("Fetched arena Elo for %d models", len(arena_elo))
    except Exception as exc:
        logger.warning("Failed to fetch arena catalog: %s", exc)

    # --- Source 2: Arena metadata (cutoff, org, license) ---
    arena_meta: dict[str, dict] = {}
    try:
        csv_filename = _discover_latest_arena_csv()
        url = _ARENA_METADATA_BASE + csv_filename
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            arena_meta = _parse_arena_metadata(resp.read().decode())
        logger.info("Fetched arena metadata for %d models from %s", len(arena_meta), csv_filename)
    except Exception as exc:
        logger.warning("Failed to fetch arena metadata: %s", exc)

    # --- Merge into annotations ---
    all_cached_models = [m for models, _ in _model_cache.values() for m in models]
    for model_id in all_cached_models:
        entry = _annotations.setdefault(model_id, {})
        metadata = entry.setdefault("metadata", {})

        # Stamp first_seen only for newly discovered models
        if "first_seen" not in metadata:
            metadata["first_seen"] = now

        # Match arena data by normalized name — apply to ALL matching providers
        norm = _normalize_model_name(model_id)
        if norm in arena_elo:
            metadata["arena_elo"] = arena_elo[norm]
        if norm in arena_meta:
            for field in ("knowledge_cutoff", "organization", "license"):
                val = arena_meta[norm].get(field)
                if val is not None:
                    metadata[field] = val

        # Remove stale livebench_avg if present (old source is dead)
        metadata.pop("livebench_avg", None)

        metadata["last_updated"] = now

    _save_annotations(_annotations)
```

- [ ] **Step 6: Update the enrichment merge test**

Replace `test_fetch_enrichment_merges_data` in `tests/test_annotations.py` with:

```python
def test_fetch_enrichment_merges_data(tmp_path, monkeypatch):
    """_fetch_enrichment merges arena Elo and metadata into annotations."""
    ann_file = tmp_path / "annotations.json"
    ann_file.write_text("{}")
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))

    # Pre-populate model cache with two providers for same model
    server._model_cache["openai"] = (["openai/gpt-5.2"], 0)
    server._model_cache["openrouter:zdr=False"] = (["openrouter/openai/gpt-5.2"], 0)
    server._annotations = {}

    # Mock arena catalog (Elo)
    arena_catalog = json.dumps({
        "full": {"gpt-5.2": {"rating": 1486.0, "rating_q975": 1493.0, "rating_q025": 1480.0}},
    })
    # Mock arena metadata CSV
    arena_csv = (
        "key,Model,MT-bench (score),MMLU,Knowledge cutoff date,License,Organization,Link\n"
        "gpt-5.2,GPT-5.2,9.1,90.5,2025/6,Proprietary,OpenAI,https://openai.com\n"
    )
    # Mock HF file listing
    hf_listing = json.dumps([{"rfilename": "leaderboard_table_20250804.csv"}])

    import urllib.request

    class FakeResponse:
        def __init__(self, data):
            self._data = data.encode()
        def read(self):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "arena-catalog" in url:
            return FakeResponse(arena_catalog)
        if "tree/main" in url:
            return FakeResponse(hf_listing)
        if "leaderboard_table" in url:
            return FakeResponse(arena_csv)
        raise ValueError(f"Unexpected URL: {url}")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    server._fetch_enrichment()

    # Both providers should get arena data (cross-pollination for Elo/cutoff)
    for model_id in ("openai/gpt-5.2", "openrouter/openai/gpt-5.2"):
        assert model_id in server._annotations
        meta = server._annotations[model_id]["metadata"]
        assert meta["arena_elo"] == 1486.0
        assert meta["knowledge_cutoff"] == "2025/6"
        assert meta["organization"] == "OpenAI"
        assert "first_seen" in meta
        assert "last_updated" in meta

    # Clean up
    server._model_cache.pop("openai", None)
    server._model_cache.pop("openrouter:zdr=False", None)
```

- [ ] **Step 7: Add test for livebench_avg cleanup**

Add to `tests/test_annotations.py`:

```python
def test_fetch_enrichment_removes_stale_livebench(tmp_path, monkeypatch):
    """_fetch_enrichment removes livebench_avg from pre-existing annotations."""
    ann_file = tmp_path / "annotations.json"
    ann_file.write_text("{}")
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))

    server._model_cache["openai"] = (["openai/gpt-5.2"], 0)
    server._annotations = {
        "openai/gpt-5.2": {"metadata": {"livebench_avg": 81.8, "first_seen": "2026-01-01T00:00:00Z"}}
    }

    import urllib.request

    class FakeResponse:
        def __init__(self, data):
            self._data = data.encode()
        def read(self):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    # Return empty data for all sources — we're testing cleanup, not enrichment
    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "arena-catalog" in url:
            return FakeResponse('{"full": {}}')
        if "tree/main" in url:
            return FakeResponse("[]")
        return FakeResponse("")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    server._fetch_enrichment()

    meta = server._annotations["openai/gpt-5.2"]["metadata"]
    assert "livebench_avg" not in meta

    server._model_cache.pop("openai", None)
```

- [ ] **Step 8: Add test for refresh_provider_models OpenRouter metadata merge**

Add to `tests/test_annotations.py`:

```python
def test_refresh_provider_models_merges_openrouter_metadata(monkeypatch):
    """_refresh_provider_models merges OpenRouter metadata into annotations."""
    monkeypatch.setattr(server, "_provider_registry", {"openrouter": "fake-key"})
    monkeypatch.setattr(server, "_zero_data_retention", False)
    server._annotations = {}
    server._model_cache.clear()

    import urllib.request

    fake_data = json.dumps({
        "data": [{
            "id": "deepseek/deepseek-v3.2",
            "context_length": 131072,
            "pricing": {"prompt": "0.0000003", "completion": "0.0000008"},
            "created": 1741564800,
        }]
    })

    class FakeResponse:
        def __init__(self, data):
            self._data = data.encode()
        def read(self):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    def mock_urlopen(req, timeout=None):
        return FakeResponse(fake_data)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    server._refresh_provider_models()

    model_id = "openrouter/deepseek/deepseek-v3.2"
    assert model_id in server._annotations
    meta = server._annotations[model_id]["metadata"]
    assert meta["context_length"] == 131072
    assert meta["pricing_in"] == "0.0000003"

    server._model_cache.clear()
    server._annotations.clear()
```

- [ ] **Step 9: Run all tests**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 10: Commit**

```bash
git add tests/test_annotations.py src/ask_another/server.py
git commit -m "feat: replace broken enrichment sources with arena-catalog + HF CSV"
```

---

## Chunk 4: Update `search_models` Output + CLAUDE.md

### Task 4: Surface new metadata fields in search results

**Files:**
- Modify: `src/ask_another/server.py:685-702` (`search_models` function body)
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `search_models` to show new fields**

In `src/ask_another/server.py`, replace the metadata formatting in `search_models` (lines 690-698):

```python
        desc_parts = []
        if meta.get("arena_elo"):
            desc_parts.append(f"Elo {meta['arena_elo']:.0f}")
        if meta.get("knowledge_cutoff"):
            desc_parts.append(f"cutoff {meta['knowledge_cutoff']}")
        if meta.get("context_length"):
            desc_parts.append(f"{meta['context_length'] // 1000}k ctx")
        if meta.get("pricing_in"):
            desc_parts.append(f"${meta['pricing_in']}/tok in")
        if note:
            desc_parts.append(note)
```

- [ ] **Step 2: Remove the `livebench_avg` reference**

The old line `if meta.get("livebench_avg"):` should already be gone from Step 1. Verify it's not referenced anywhere else:

Run: `grep -n "livebench" src/ask_another/server.py`
Expected: No matches

- [ ] **Step 3: Update CLAUDE.md**

In `CLAUDE.md`, update the annotations schema example to replace `livebench_avg` with the new fields, update `search_models` description to mention new metadata, and update the enrichment source references from "LiveBench (HuggingFace CSV) and LMArena (HuggingFace CSV)" to "LMArena arena-catalog (GitHub JSON) and LMArena metadata (HuggingFace CSV)".

- [ ] **Step 4: Run all tests to verify nothing broke**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ask_another/server.py CLAUDE.md
git commit -m "feat: surface knowledge_cutoff and pricing in search_models, update docs"
```

---

## Chunk 5: Cleanup + Final Verification

### Task 5: Remove dead code and run full test suite

**Files:**
- Modify: `src/ask_another/server.py` (verify old constants/parsers are gone)

- [ ] **Step 1: Verify dead code is removed**

Run: `grep -n "LIVEBENCH\|_parse_livebench\|_parse_lmarena\|_LMARENA_URL" src/ask_another/server.py`
Expected: No matches (all removed in Chunk 3)

- [ ] **Step 2: Run full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: remove dead enrichment code"
```

- [ ] **Step 4: Push**

```bash
git push
```
