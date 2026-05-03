"""End-to-end search_models / search_families against live provider data."""
from __future__ import annotations

import pytest

import ask_another.server as server

pytestmark = pytest.mark.integration


def test_search_models_finds_gpt_5(openai_key: str) -> None:
    out = server.search_models(search="gpt-5")
    lines = [line for line in out.splitlines() if line and not line.startswith("⚠️")]
    assert any("openai/gpt-5" in line for line in lines), out


def test_search_models_surfaces_metadata(openai_key: str) -> None:
    """At least one result should carry enrichment metadata (Elo / ctx / pricing)."""
    out = server.search_models(search="gpt-5")
    has_meta = any(" — " in line for line in out.splitlines())
    assert has_meta, f"No enrichment metadata in:\n{out}"


def test_search_families_lists_each_provider(configured_providers: list[str]) -> None:
    out = server.search_families()
    families = set(out.splitlines())
    for p in configured_providers:
        assert any(f == p or f.startswith(f"{p}/") for f in families), (
            f"Provider '{p}' has no families in:\n{out}"
        )


def test_search_families_filter(configured_providers: list[str]) -> None:
    if "openrouter" not in configured_providers:
        pytest.skip("openrouter not configured")
    out = server.search_families(search="openrouter")
    assert out.strip(), "Filtered search_families returned empty"
    for line in out.splitlines():
        if line and not line.startswith("⚠️"):
            assert "openrouter" in line.lower(), f"Unexpected family in filter: {line}"


def test_search_models_excludes_non_zdr_research_models(openrouter_key: str) -> None:
    """The specific feedback regression: o3/o4-deep-research must be filtered
    out when ZDR is on, and reappear when ZDR is off.
    """
    non_zdr_ids = [
        "openrouter/openai/o3-deep-research",
        "openrouter/openai/o4-mini-deep-research",
    ]
    on_ids = {
        line.split(" — ")[0]
        for line in server.search_models(search="deep-research", zdr=True).splitlines()
        if line.startswith("openrouter/")
    }
    off_ids = {
        line.split(" — ")[0]
        for line in server.search_models(search="deep-research", zdr=False).splitlines()
        if line.startswith("openrouter/")
    }
    for m in non_zdr_ids:
        assert m not in on_ids, f"{m} surfaced under ZDR=True (feedback regression)"
        assert m in off_ids, f"{m} missing under ZDR=False — OpenRouter may have removed it"
