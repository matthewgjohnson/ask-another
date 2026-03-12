"""Tests for the annotations system."""

import json
from datetime import datetime, timezone, timedelta
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
