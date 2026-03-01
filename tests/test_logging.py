"""Tests for debug logging configuration."""

import logging
import logging.handlers
import os
from pathlib import Path
from unittest.mock import patch

import ask_another.server as server


def _clear_logger():
    """Remove all handlers from the server logger."""
    for h in server.logger.handlers[:]:
        server.logger.removeHandler(h)
    server.logger.setLevel(logging.WARNING)


def test_no_handler_when_log_level_unset(monkeypatch: "pytest.MonkeyPatch"):
    """No handler is added when LOG_LEVEL is empty."""
    _clear_logger()
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    server._configure_logging()

    assert not any(
        isinstance(h, logging.handlers.RotatingFileHandler)
        for h in server.logger.handlers
    )


def test_handler_added_when_log_level_set(monkeypatch: "pytest.MonkeyPatch", tmp_path: Path):
    """RotatingFileHandler is added when LOG_LEVEL is set."""
    _clear_logger()
    log_file = tmp_path / "test.log"
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FILE", str(log_file))

    server._configure_logging()

    handlers = [
        h for h in server.logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(handlers) == 1
    assert handlers[0].baseFilename == str(log_file)
    assert server.logger.level == logging.DEBUG

    _clear_logger()


def test_log_file_size_and_count(monkeypatch: "pytest.MonkeyPatch", tmp_path: Path):
    """LOG_FILE_SIZE and LOG_FILE_COUNT are respected."""
    _clear_logger()
    log_file = tmp_path / "test.log"
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FILE", str(log_file))
    monkeypatch.setenv("LOG_FILE_SIZE", "10")
    monkeypatch.setenv("LOG_FILE_COUNT", "5")

    server._configure_logging()

    handlers = [
        h for h in server.logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(handlers) == 1
    assert handlers[0].maxBytes == 10 * 1024 * 1024
    assert handlers[0].backupCount == 5

    _clear_logger()


def test_invalid_log_level_ignored(monkeypatch: "pytest.MonkeyPatch"):
    """Invalid LOG_LEVEL value is silently ignored."""
    _clear_logger()
    monkeypatch.setenv("LOG_LEVEL", "NOTAVALIDLEVEL")

    server._configure_logging()

    assert not any(
        isinstance(h, logging.handlers.RotatingFileHandler)
        for h in server.logger.handlers
    )


def test_invalid_size_and_count_use_defaults(monkeypatch: "pytest.MonkeyPatch", tmp_path: Path):
    """Non-numeric LOG_FILE_SIZE and LOG_FILE_COUNT fall back to defaults."""
    _clear_logger()
    log_file = tmp_path / "test.log"
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FILE", str(log_file))
    monkeypatch.setenv("LOG_FILE_SIZE", "notanumber")
    monkeypatch.setenv("LOG_FILE_COUNT", "alsonotanumber")

    server._configure_logging()

    handlers = [
        h for h in server.logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(handlers) == 1
    assert handlers[0].maxBytes == 5 * 1024 * 1024
    assert handlers[0].backupCount == 2

    _clear_logger()


def test_exception_logging(monkeypatch: "pytest.MonkeyPatch", tmp_path: Path):
    """Silent exception blocks now produce log output."""
    _clear_logger()
    log_file = tmp_path / "test.log"
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FILE", str(log_file))
    server._configure_logging()

    # Simulate _fetch_models raising for a provider
    monkeypatch.setattr(server, "_provider_registry", {"fakeprovider": "key123"})
    monkeypatch.setattr(server, "_model_cache", {})

    def _raise_on_fetch(provider, api_key, *, zdr=False):
        raise ConnectionError("simulated network failure")

    monkeypatch.setattr(server, "_fetch_models", _raise_on_fetch)

    result = server._get_models("fakeprovider")
    assert result == []

    log_content = log_file.read_text()
    assert "fakeprovider" in log_content
    assert "simulated network failure" in log_content

    _clear_logger()
