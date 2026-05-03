"""Live enrichment fetches: arena-catalog, HF metadata CSV, OpenRouter /models, ZDR."""
from __future__ import annotations

import pytest

import ask_another.server as server

pytestmark = pytest.mark.integration

# Models that OpenRouter explicitly excludes from ZDR (we know from feedback).
KNOWN_NON_ZDR_OPENROUTER = [
    "openrouter/openai/o3-deep-research",
    "openrouter/openai/o4-mini-deep-research",
]


def test_fetch_enrichment_populates_annotations(configured_providers: list[str]) -> None:
    """arena-catalog + HF CSV parse and at least one model gets an arena_elo.

    `_fetch_enrichment` merges into the global `_annotations` dict in place
    rather than returning data — so we verify by inspecting the annotations
    after the call.
    """
    # Make sure the model cache is populated so enrichment has something to merge into.
    server._model_cache.clear()
    server._refresh_provider_models()
    server._fetch_enrichment()

    has_elo = any(
        entry.get("metadata", {}).get("arena_elo") is not None
        for entry in server._annotations.values()
    )
    assert has_elo, "No model received arena_elo after enrichment — parser likely broken"


def test_fetch_openrouter_zdr_excludes_known_non_zdr(openrouter_key: str) -> None:
    """ZDR endpoint must exclude models that explicitly aren't ZDR-compatible.

    Note: we don't assert ZDR is a subset of /models — the ZDR endpoint
    actually surfaces specialized models (embeddings, audio, video) that
    aren't in the chat /models listing. Instead we check the specific
    failure mode from the feedback log.
    """
    full, _ = server._fetch_openrouter_models(openrouter_key, zdr=False)
    zdr, _ = server._fetch_openrouter_models(openrouter_key, zdr=True)
    assert full, "OpenRouter /models returned empty"
    assert zdr, "OpenRouter ZDR endpoint returned empty"
    full_set = set(full)
    zdr_set = set(zdr)

    for non_zdr in KNOWN_NON_ZDR_OPENROUTER:
        if non_zdr in full_set:
            assert non_zdr not in zdr_set, (
                f"{non_zdr} listed as ZDR-compatible — feedback regression"
            )

    # Sanity: the two lists should at least share the popular chat models.
    assert len(full_set & zdr_set) > 5, (
        f"ZDR and /models share too few entries ({len(full_set & zdr_set)}) — "
        "one of the endpoints likely broke"
    )


def test_fetch_openrouter_models_have_pricing(openrouter_key: str) -> None:
    """OpenRouter metadata contains pricing for at least some models."""
    _, meta = server._fetch_openrouter_models(openrouter_key, zdr=True)
    has_pricing = any(m.get("pricing_in") is not None for m in meta.values())
    assert has_pricing, "No OpenRouter models had pricing_in metadata"
