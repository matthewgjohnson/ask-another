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
