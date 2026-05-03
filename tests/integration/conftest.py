"""Shared fixtures for live integration tests.

Tests in this directory hit real provider APIs. They auto-skip when the
relevant PROVIDER_* env vars are missing, so a partial key set still runs
the subset of tests that have credentials.

All tests are marked @pytest.mark.integration and excluded from the
default suite via pyproject.toml addopts.
"""
from __future__ import annotations

import os

import pytest

import ask_another.server as server


@pytest.fixture(scope="session", autouse=True)
def _live_config() -> None:
    """Load env-based config once per session so module globals are populated.

    Doesn't skip when no providers are set — the MCP smoke tests run without
    keys. Tests that need a specific provider should use the per-provider
    fixtures below, which skip individually when their key is missing.
    """
    if any(k.startswith("PROVIDER_") for k in os.environ):
        server._load_config()


def _require_provider(name: str) -> str:
    """Skip the calling test if the named provider isn't configured."""
    key = server._provider_registry.get(name)
    if not key:
        pytest.skip(f"Provider '{name}' not configured")
    return key


@pytest.fixture
def openai_key() -> str:
    return _require_provider("openai")


@pytest.fixture
def gemini_key() -> str:
    return _require_provider("gemini")


@pytest.fixture
def openrouter_key() -> str:
    return _require_provider("openrouter")


@pytest.fixture(scope="session")
def configured_providers() -> list[str]:
    return sorted(server._provider_registry.keys())
