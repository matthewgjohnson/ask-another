"""Tests for PSV model catalog loading and integration."""

from pathlib import Path

import ask_another.server as server


PSV_CONTENT = """\
model|context|tok_sec|price_in|price_out|aa_index|arena_elo|swe_bench|gpqa|favourite|description
gemini/gemini-test|1000000|91|2.00|12.00|57|1500|80.6|94.3|yes|Top model, best quality
openrouter/test/model-a|200000|66|1.00|3.20|50|1451|77.8|86.0|no|Good open-weight model
openai/test-coder|128000||0.55|2.19|27||57.6|81.0|yes|Best for coding tasks
"""


def _write_psv(tmp_path: Path) -> Path:
    psv_file = tmp_path / "models.psv"
    psv_file.write_text(PSV_CONTENT)
    return psv_file


def test_load_psv_parses_file(tmp_path: Path, monkeypatch: object):
    """_load_psv reads a PSV file and returns correct ModelMeta entries."""
    psv_file = _write_psv(tmp_path)
    monkeypatch.setenv("MODELS_PSV", str(psv_file))

    catalog = server._load_psv()

    assert len(catalog) == 3
    assert "gemini/gemini-test" in catalog
    assert catalog["gemini/gemini-test"].favourite is True
    assert catalog["gemini/gemini-test"].description == "Top model, best quality"
    assert catalog["openrouter/test/model-a"].favourite is False
    assert catalog["openai/test-coder"].favourite is True


def test_load_psv_missing_file(monkeypatch: object):
    """_load_psv returns empty dict when the file doesn't exist."""
    monkeypatch.setenv("MODELS_PSV", "/nonexistent/models.psv")

    catalog = server._load_psv()

    assert catalog == {}


def test_load_psv_skips_header_and_blanks(tmp_path: Path, monkeypatch: object):
    """_load_psv skips the header row and blank lines."""
    psv_file = tmp_path / "models.psv"
    psv_file.write_text(
        "model|context|tok_sec|price_in|price_out|aa_index|arena_elo|swe_bench|gpqa|favourite|description\n"
        "\n"
        "openai/test|128000||1.00|4.00|||||yes|A test model\n"
        "\n"
    )
    monkeypatch.setenv("MODELS_PSV", str(psv_file))

    catalog = server._load_psv()

    assert len(catalog) == 1
    assert "openai/test" in catalog


def test_favourites_bootstrap_from_psv(tmp_path: Path, monkeypatch: object):
    """When FAVOURITES env var is empty, favourites come from PSV."""
    psv_file = _write_psv(tmp_path)
    monkeypatch.setenv("MODELS_PSV", str(psv_file))
    monkeypatch.delenv("FAVOURITES", raising=False)
    # Need at least one provider for _load_config to work
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")

    server._load_config()

    assert "gemini/gemini-test" in server._favourites
    assert "openai/test-coder" in server._favourites
    assert "openrouter/test/model-a" not in server._favourites


def test_favourites_env_overrides_psv(tmp_path: Path, monkeypatch: object):
    """When FAVOURITES env var is set, PSV favourites are ignored."""
    psv_file = _write_psv(tmp_path)
    monkeypatch.setenv("MODELS_PSV", str(psv_file))
    monkeypatch.setenv("FAVOURITES", "openai/custom-model")
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")

    server._load_config()

    assert server._favourites == ["openai/custom-model"]
    # Catalog is still loaded
    assert "gemini/gemini-test" in server._model_catalog


def test_build_instructions_includes_descriptions(tmp_path: Path, monkeypatch: object):
    """_build_instructions includes descriptions from the catalog."""
    psv_file = _write_psv(tmp_path)
    monkeypatch.setenv("MODELS_PSV", str(psv_file))
    monkeypatch.delenv("FAVOURITES", raising=False)
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")

    server._load_config()
    instructions = server._build_instructions()

    assert "gemini/gemini-test — Top model, best quality" in instructions
    assert "openai/test-coder — Best for coding tasks" in instructions


def test_search_models_includes_descriptions(tmp_path: Path, monkeypatch: object):
    """search_models enriches results with descriptions from the PSV catalog."""
    psv_file = _write_psv(tmp_path)
    monkeypatch.setenv("MODELS_PSV", str(psv_file))
    monkeypatch.delenv("FAVOURITES", raising=False)
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")

    server._load_config()
    monkeypatch.setattr(
        server, "_get_models",
        lambda provider=None, *, zdr=None: [
            "gemini/gemini-test",
            "openrouter/test/model-a",
            "openai/test-coder",
        ],
    )
    result = server.search_models()

    # Favourite with description
    assert "gemini/gemini-test — Top model, best quality" in result
    # Non-favourite with description
    assert "openrouter/test/model-a — Good open-weight model" in result
    # Favourite with description
    assert "openai/test-coder — Best for coding tasks" in result


def test_search_models_bare_ids_without_psv(tmp_path: Path, monkeypatch: object):
    """Models not in the PSV catalog appear as bare IDs without descriptions."""
    psv_file = _write_psv(tmp_path)
    monkeypatch.setenv("MODELS_PSV", str(psv_file))
    monkeypatch.delenv("FAVOURITES", raising=False)
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")

    server._load_config()
    monkeypatch.setattr(
        server, "_get_models",
        lambda provider=None, *, zdr=None: ["openai/unknown-model", "openai/test-coder"],
    )
    result = server.search_models()

    assert "openai/unknown-model" in result
    assert "openai/unknown-model —" not in result
    assert "openai/test-coder — Best for coding tasks" in result


def test_zero_data_retention_flag(monkeypatch: object):
    """ZERO_DATA_RETENTION env var sets the _zero_data_retention global."""
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.delenv("FAVOURITES", raising=False)
    monkeypatch.setenv("ZERO_DATA_RETENTION", "true")

    server._load_config()

    assert server._zero_data_retention is True


def test_zero_data_retention_default(monkeypatch: object):
    """ZERO_DATA_RETENTION defaults to True when not set."""
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.delenv("FAVOURITES", raising=False)
    monkeypatch.delenv("ZERO_DATA_RETENTION", raising=False)

    server._load_config()

    assert server._zero_data_retention is True


def test_zero_data_retention_opt_out(monkeypatch: object):
    """ZERO_DATA_RETENTION can be explicitly disabled."""
    monkeypatch.setenv("PROVIDER_TEST", "openai;sk-test")
    monkeypatch.delenv("FAVOURITES", raising=False)
    monkeypatch.setenv("ZERO_DATA_RETENTION", "false")

    server._load_config()

    assert server._zero_data_retention is False
