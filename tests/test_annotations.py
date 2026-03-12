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
