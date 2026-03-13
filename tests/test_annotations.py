"""Tests for the annotations system."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import ask_another.server as server


# -- Shared test doubles --

class FakeUrlResponse:
    """Mock for urllib.request.urlopen responses."""
    def __init__(self, data):
        self._data = data.encode()
    def read(self):
        return self._data
    def __enter__(self):
        return self
    def __exit__(self, *a):
        pass


class _FakeChoice:
    class message:
        content = "Hello"


class FakeLlmResponse:
    """Mock for litellm.completion responses."""
    choices = [_FakeChoice()]


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


def test_completion_tracks_usage(tmp_path, monkeypatch):
    """completion() increments call_count and updates last_used."""
    ann_file = tmp_path / "annotations.json"
    ann_file.write_text("{}")
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    server._load_config()
    server._annotations = server._load_annotations()

    # Mock _resolve_model and litellm.completion
    monkeypatch.setattr(server, "_resolve_model", lambda m: ("openai/gpt-5.2", "sk-test"))
    monkeypatch.setattr(server, "_get_models", lambda provider=None, *, zdr=None: ["openai/gpt-5.2"])

    import litellm
    monkeypatch.setattr(litellm, "completion", lambda **kw: FakeLlmResponse())

    server.completion(model="openai/gpt-5.2", prompt="hi")

    loaded = json.loads(ann_file.read_text())
    assert loaded["openai/gpt-5.2"]["usage"]["call_count"] == 1

    # Call again
    server.completion(model="openai/gpt-5.2", prompt="hi again")
    loaded = json.loads(ann_file.read_text())
    assert loaded["openai/gpt-5.2"]["usage"]["call_count"] == 2


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


def test_get_recent_models():
    """Models first seen within last 7 days are returned, newest first."""
    now = datetime.now(timezone.utc)
    annotations = {
        "openai/new-model": {
            "metadata": {"first_seen": now.isoformat()}
        },
        "openai/old-model": {
            "metadata": {"first_seen": (now - timedelta(days=30)).isoformat()}
        },
        "openai/recent-model": {
            "metadata": {"first_seen": (now - timedelta(days=3)).isoformat()}
        },
    }
    result = server._get_recent_models(annotations, days=7)
    assert len(result) == 2
    assert result[0][0] == "openai/new-model"
    assert result[1][0] == "openai/recent-model"


def test_build_instructions_from_usage(monkeypatch):
    """Instructions surface top models by usage, highest call_count first."""
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
    assert "openai/gpt-5.2" in instructions
    assert "openai/gpt-4o" in instructions
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


def test_zero_data_retention_flag(monkeypatch):
    """ZERO_DATA_RETENTION env var sets the _zero_data_retention global."""
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.setenv("ZERO_DATA_RETENTION", "true")

    server._load_config()

    assert server._zero_data_retention is True


def test_zero_data_retention_default(monkeypatch):
    """ZERO_DATA_RETENTION defaults to True when not set."""
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.delenv("ZERO_DATA_RETENTION", raising=False)

    server._load_config()

    assert server._zero_data_retention is True


def test_zero_data_retention_opt_out(monkeypatch):
    """ZERO_DATA_RETENTION can be explicitly disabled."""
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.setenv("ZERO_DATA_RETENTION", "false")

    server._load_config()

    assert server._zero_data_retention is False


def test_refresh_provider_models(tmp_path, monkeypatch):
    """_refresh_provider_models populates the model cache from providers."""
    ann_file = tmp_path / "annotations.json"
    ann_file.write_text("{}")
    monkeypatch.setenv("ANNOTATIONS_FILE", str(ann_file))
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.setenv("CACHE_TTL_MINUTES", "360")

    monkeypatch.setattr(
        server, "_fetch_models",
        lambda provider, api_key, *, zdr=False: ["openai/gpt-5.2", "openai/gpt-4o"],
    )

    server._load_config()
    server._model_cache.clear()
    server._refresh_provider_models()

    all_cached = [m for models, _ in server._model_cache.values() for m in models]
    assert "openai/gpt-5.2" in all_cached
    assert "openai/gpt-4o" in all_cached


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

    def mock_urlopen(req, timeout=None):
        return FakeUrlResponse(file_listing)

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

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "arena-catalog" in url:
            return FakeUrlResponse(arena_catalog)
        if "tree/main" in url:
            return FakeUrlResponse(hf_listing)
        if "leaderboard_table" in url:
            return FakeUrlResponse(arena_csv)
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

    # Return empty data for all sources — we're testing cleanup, not enrichment
    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "arena-catalog" in url:
            return FakeUrlResponse('{"full": {}}')
        if "tree/main" in url:
            return FakeUrlResponse("[]")
        return FakeUrlResponse("")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    server._fetch_enrichment()

    meta = server._annotations["openai/gpt-5.2"]["metadata"]
    assert "livebench_avg" not in meta

    server._model_cache.pop("openai", None)


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

    def mock_urlopen(req, timeout=None):
        return FakeUrlResponse(fake_data)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    server._refresh_provider_models()

    model_id = "openrouter/deepseek/deepseek-v3.2"
    assert model_id in server._annotations
    meta = server._annotations[model_id]["metadata"]
    assert meta["context_length"] == 131072
    assert meta["pricing_in"] == "0.0000003"

    server._model_cache.clear()
    server._annotations.clear()


def test_needs_refresh_no_annotations():
    """Empty annotations means refresh is needed."""
    assert server._needs_refresh({}) is True


def test_needs_refresh_stale(monkeypatch):
    """Annotations older than TTL need refresh."""
    monkeypatch.setattr(server, "_cache_ttl_minutes", 1)
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


def test_needs_refresh_ignores_usage_only(monkeypatch):
    """Usage-only entries (no metadata) don't trigger a refresh."""
    monkeypatch.setattr(server, "_cache_ttl_minutes", 99999)
    annotations = {
        "openai/gpt-5.2": {
            "metadata": {"last_updated": datetime.now(timezone.utc).isoformat()}
        },
        "openai/gpt-4o": {
            "usage": {"call_count": 3, "last_used": "2026-03-12T00:00:00Z"}
        },
    }
    assert server._needs_refresh(annotations) is False


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

    def mock_urlopen(req, timeout=None):
        return FakeUrlResponse(fake_response_data)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    models, metadata = server._fetch_openrouter_models("fake-key")
    assert "openrouter/deepseek/deepseek-v3.2" in models
    assert "openrouter/openai/gpt-5.2" in models

    meta = metadata["openrouter/deepseek/deepseek-v3.2"]
    assert meta["context_length"] == 131072
    assert meta["pricing_in"] == "0.0000003"
    assert meta["pricing_out"] == "0.0000008"
    assert meta["openrouter_listed"] == 1741564800


def test_fetch_openrouter_models_zdr_returns_metadata_for_zdr_models(monkeypatch):
    """ZDR path fetches metadata from public endpoint, filters to ZDR models."""
    import urllib.request

    fake_public = json.dumps({
        "data": [
            {
                "id": "deepseek/deepseek-v3.2",
                "context_length": 131072,
                "pricing": {"prompt": "0.0000003", "completion": "0.0000008"},
                "created": 1741564800,
            },
            {
                "id": "some/non-zdr-model",
                "context_length": 8192,
                "pricing": {"prompt": "0.001", "completion": "0.002"},
                "created": 1700000000,
            },
        ]
    })
    fake_zdr = json.dumps({
        "data": [
            {"model_id": "deepseek/deepseek-v3.2"},
        ]
    })

    def mock_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "endpoints/zdr" in url:
            return FakeUrlResponse(fake_zdr)
        return FakeUrlResponse(fake_public)

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    models, metadata = server._fetch_openrouter_models("fake-key", zdr=True)
    assert "openrouter/deepseek/deepseek-v3.2" in models
    assert "openrouter/some/non-zdr-model" not in models
    assert "openrouter/deepseek/deepseek-v3.2" in metadata
    assert metadata["openrouter/deepseek/deepseek-v3.2"]["context_length"] == 131072
    assert "openrouter/some/non-zdr-model" not in metadata


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


def test_resolve_model_discovery_fallback_by_elo(monkeypatch):
    """Shorthand falls back to discovered models, picking highest Elo."""
    monkeypatch.setattr(server, "_annotations", {
        "openai/gpt-4o": {"metadata": {"arena_elo": 1200}},
        "openai/gpt-5.2": {"metadata": {"arena_elo": 1486}},
        "openai/gpt-5.4": {"metadata": {"arena_elo": 1510}},
    })
    monkeypatch.setattr(server, "_provider_registry", {"openai": "sk-test"})
    monkeypatch.setattr(
        server, "_get_models",
        lambda provider=None, *, zdr=None: [
            "openai/gpt-4o", "openai/gpt-5.2", "openai/gpt-5.4",
        ],
    )
    # No favourites — empty usage
    full_id, api_key = server._resolve_model("openai")
    assert full_id == "openai/gpt-5.4"
    assert api_key == "sk-test"


def test_resolve_model_discovery_fallback_elo_tiebreak(monkeypatch):
    """On equal Elo, discovery fallback picks first alphabetically."""
    monkeypatch.setattr(server, "_annotations", {
        "openai/model-b": {"metadata": {"arena_elo": 1400}},
        "openai/model-a": {"metadata": {"arena_elo": 1400}},
    })
    monkeypatch.setattr(server, "_provider_registry", {"openai": "sk-test"})
    monkeypatch.setattr(
        server, "_get_models",
        lambda provider=None, *, zdr=None: [
            "openai/model-a", "openai/model-b",
        ],
    )
    full_id, _ = server._resolve_model("openai")
    assert full_id == "openai/model-a"


def test_resolve_model_no_match_raises(monkeypatch):
    """Unknown shorthand raises ValueError with helpful message."""
    monkeypatch.setattr(server, "_annotations", {})
    monkeypatch.setattr(server, "_provider_registry", {"openai": "sk-test"})
    monkeypatch.setattr(
        server, "_get_models",
        lambda provider=None, *, zdr=None: ["openai/gpt-5.2"],
    )
    with pytest.raises(ValueError, match="No models found matching 'nonexistent'"):
        server._resolve_model("nonexistent")


def test_resolve_model_full_id_direct(monkeypatch):
    """Full model ID routes directly without needing favourites or discovery."""
    monkeypatch.setattr(server, "_annotations", {})
    monkeypatch.setattr(server, "_provider_registry", {"openai": "sk-test"})
    full_id, api_key = server._resolve_model("openai/gpt-5.2")
    assert full_id == "openai/gpt-5.2"
    assert api_key == "sk-test"


def test_build_instructions_includes_elo_section(monkeypatch):
    """Instructions include top-rated models by Elo."""
    monkeypatch.setattr(server, "_annotations", {
        "openai/gpt-5.4": {"metadata": {"arena_elo": 1510}},
        "openai/gpt-5.2": {"metadata": {"arena_elo": 1486}},
        "gemini/gemini-3.5-pro": {"metadata": {"arena_elo": 1497}},
    })
    instructions = server._build_instructions()
    assert "Top Rated Models (by Elo):" in instructions
    assert "Elo 1510" in instructions
    assert "Elo 1497" in instructions
    # Verify ordering: 1510 appears before 1497
    assert instructions.index("Elo 1510") < instructions.index("Elo 1497")


def test_build_instructions_elo_and_favourites_coexist(monkeypatch):
    """Instructions show both favourites and top-rated sections."""
    monkeypatch.setattr(server, "_annotations", {
        "openai/gpt-5.2": {
            "metadata": {"arena_elo": 1486},
            "usage": {"call_count": 10, "last_used": "2026-03-12T00:00:00Z"},
        },
    })
    instructions = server._build_instructions()
    assert "Favourite Models:" in instructions
    assert "Top Rated Models (by Elo):" in instructions


def test_build_instructions_elo_deduplicates_providers(monkeypatch):
    """Same model via different providers only appears once in Top Rated."""
    monkeypatch.setattr(server, "_annotations", {
        "openai/gpt-5.4": {"metadata": {"arena_elo": 1510}},
        "openrouter/openai/gpt-5.4": {"metadata": {"arena_elo": 1510}},
        "gemini/gemini-3.5-pro": {"metadata": {"arena_elo": 1497}},
    })
    instructions = server._build_instructions()
    # gpt-5.4 should appear only once despite two providers
    assert instructions.count("gpt-5.4") == 1
    assert "gemini-3.5-pro" in instructions
