"""Tests for the feedback tool."""

import json
import tempfile
from pathlib import Path

import ask_another.server as server


def test_feedback_writes_entry(tmp_path: Path):
    """Feedback tool writes a JSON-lines entry to the log file."""
    log_file = tmp_path / "feedback.jsonl"
    server._feedback_log = log_file

    result = server.feedback(issue="search_models returned empty string", tool_name="search_models")

    assert result == "Feedback recorded. Thank you."
    assert log_file.exists()

    entry = json.loads(log_file.read_text().strip())
    assert entry["issue"] == "search_models returned empty string"
    assert entry["tool_name"] == "search_models"
    assert "timestamp" in entry


def test_feedback_without_tool_name(tmp_path: Path):
    """Feedback tool works without a tool_name."""
    log_file = tmp_path / "feedback.jsonl"
    server._feedback_log = log_file

    server.feedback(issue="unclear how to proceed")

    entry = json.loads(log_file.read_text().strip())
    assert entry["issue"] == "unclear how to proceed"
    assert "tool_name" not in entry


def test_feedback_appends_multiple(tmp_path: Path):
    """Multiple feedback calls append to the same file."""
    log_file = tmp_path / "feedback.jsonl"
    server._feedback_log = log_file

    server.feedback(issue="first issue")
    server.feedback(issue="second issue")

    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["issue"] == "first issue"
    assert json.loads(lines[1])["issue"] == "second issue"
