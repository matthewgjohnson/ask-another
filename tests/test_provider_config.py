"""Tests for _parse_provider_config — supports both bare-key and legacy
prefixed formats."""
from __future__ import annotations

import pytest

from ask_another.server import _parse_provider_config


class TestBareKeyFormat:
    """PROVIDER_OPENAI=sk-... — provider derived from env var suffix."""

    def test_simple_bare_key(self):
        assert _parse_provider_config("PROVIDER_OPENAI", "sk-test") == ("openai", "sk-test")

    def test_lowercases_provider_suffix(self):
        # Env var suffixes are typically uppercase by convention; we
        # lowercase to match litellm's provider naming.
        assert _parse_provider_config("PROVIDER_GEMINI", "abc123") == ("gemini", "abc123")

    def test_strips_whitespace(self):
        assert _parse_provider_config("PROVIDER_OPENAI", "  sk-test  ") == ("openai", "sk-test")

    def test_multi_word_suffix_preserved(self):
        # Hypothetical: PROVIDER_AZURE_OPENAI=...
        assert _parse_provider_config("PROVIDER_AZURE_OPENAI", "key") == ("azure_openai", "key")


class TestLegacyPrefixedFormat:
    """PROVIDER_OPENAI=openai;sk-... — prefix in value wins."""

    def test_simple_prefixed(self):
        assert _parse_provider_config("PROVIDER_OPENAI", "openai;sk-test") == ("openai", "sk-test")

    def test_prefix_overrides_suffix(self):
        # Old configs sometimes used PROVIDER_FOO=bar;key — the prefix
        # is what registers, not the suffix.
        assert _parse_provider_config("PROVIDER_FOO", "openrouter;sk-or-x") == ("openrouter", "sk-or-x")

    def test_strips_whitespace_around_each_part(self):
        assert _parse_provider_config("PROVIDER_OPENAI", " openai ; sk-test ") == ("openai", "sk-test")

    def test_semicolon_in_key_split_only_once(self):
        # Some keys (legitimately) contain semicolons after the first one
        assert _parse_provider_config("PROVIDER_X", "openai;sk-abc;def") == ("openai", "sk-abc;def")


class TestErrors:
    def test_empty_value_raises(self):
        with pytest.raises(ValueError, match="value is empty"):
            _parse_provider_config("PROVIDER_OPENAI", "")

    def test_whitespace_only_value_raises(self):
        with pytest.raises(ValueError, match="value is empty"):
            _parse_provider_config("PROVIDER_OPENAI", "   ")

    def test_legacy_format_empty_provider_raises(self):
        with pytest.raises(ValueError, match="provider name is empty"):
            _parse_provider_config("PROVIDER_OPENAI", ";sk-test")

    def test_legacy_format_empty_key_raises(self):
        with pytest.raises(ValueError, match="API key is empty"):
            _parse_provider_config("PROVIDER_OPENAI", "openai;")

    def test_var_name_without_provider_prefix_suffix(self):
        # Edge case: PROVIDER_ alone has no suffix
        with pytest.raises(ValueError, match="Cannot derive provider name"):
            _parse_provider_config("PROVIDER_", "sk-test")


import json
import os
from pathlib import Path
from unittest.mock import patch

from ask_another import server as ask_another_server
from ask_another.server import _provider_status


def _make_mcpb_layout(
    tmp_path: Path, *, user_config: dict | None = None
) -> Path:
    """Create an MCPB-style fixture: manifest.json at root, stub server.py
    inside src/ask_another/. Returns the stub server.py path."""
    manifest = {"user_config": user_config} if user_config is not None else {}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    server_path = tmp_path / "src" / "ask_another" / "server.py"
    server_path.parent.mkdir(parents=True)
    server_path.write_text("# stub")
    return server_path


def _make_plugin_layout(
    tmp_path: Path, *, user_config: dict | None = None
) -> Path:
    """Create a Claude Code plugin-style fixture: .claude-plugin/plugin.json
    at root, stub server.py inside src/ask_another/. Returns the stub
    server.py path."""
    manifest = {"user_config": user_config} if user_config is not None else {}
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
    server_path = tmp_path / "src" / "ask_another" / "server.py"
    server_path.parent.mkdir(parents=True)
    server_path.write_text("# stub")
    return server_path


class TestProviderStatus:
    """_provider_status() resolves the plugin manifest via a three-step
    lookup (explicit arg → CLAUDE_PLUGIN_ROOT → walk-up from server file),
    parses it for declared providers, and composes them with the runtime
    _provider_registry and _provider_errors into (name, status) pairs."""

    def _snapshot(self):
        return (
            dict(ask_another_server._provider_registry),
            dict(ask_another_server._provider_errors),
        )

    def _restore(self, snap):
        registry, errors = snap
        ask_another_server._provider_registry = registry
        ask_another_server._provider_errors = errors

    # --- Manifest discovery: explicit arg ---

    def test_explicit_manifest_path_used(self, tmp_path: Path, monkeypatch):
        manifest_path = tmp_path / "custom.json"
        manifest_path.write_text(json.dumps({
            "user_config": {"provider_openai": {"type": "string"}}
        }))
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status(manifest_path=manifest_path)
            assert result == [("openai", "not configured")]
        finally:
            self._restore(snap)

    def test_nonexistent_explicit_path_falls_through(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = _make_mcpb_layout(
            tmp_path,
            user_config={"provider_openai": {"type": "string"}},
        )
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status(
                manifest_path=tmp_path / "does-not-exist.json",
                start_path=server_path,
            )
            assert result == [("openai", "not configured")]
        finally:
            self._restore(snap)

    # --- Manifest discovery: CLAUDE_PLUGIN_ROOT env var ---

    def test_claude_plugin_root_with_plugin_layout(
        self, tmp_path: Path, monkeypatch
    ):
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "user_config": {
                "provider_openai": {"type": "string"},
                "provider_gemini": {"type": "string"},
            }
        }))
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status()
            assert [name for name, _ in result] == ["openai", "gemini"]
        finally:
            self._restore(snap)

    def test_claude_plugin_root_with_mcpb_layout(
        self, tmp_path: Path, monkeypatch
    ):
        (tmp_path / "manifest.json").write_text(json.dumps({
            "user_config": {"provider_openai": {"type": "string"}}
        }))
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status()
            assert [name for name, _ in result] == ["openai"]
        finally:
            self._restore(snap)

    def test_claude_plugin_root_with_no_manifest_falls_through(
        self, tmp_path: Path, monkeypatch
    ):
        # CLAUDE_PLUGIN_ROOT points at an empty dir → fall back to walk-up.
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(empty))
        server_path = _make_mcpb_layout(
            tmp_path,
            user_config={"provider_gemini": {"type": "string"}},
        )
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status(start_path=server_path)
            assert [name for name, _ in result] == ["gemini"]
        finally:
            self._restore(snap)

    # --- Manifest discovery: walk-up fallback ---

    def test_finds_mcpb_manifest_via_walk_up(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = _make_mcpb_layout(
            tmp_path,
            user_config={
                "provider_openai": {"type": "string"},
                "provider_gemini": {"type": "string"},
                "provider_openrouter": {"type": "string"},
                "zero_data_retention": {"type": "boolean"},
            },
        )
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status(start_path=server_path)
            assert result == [
                ("openai", "not configured"),
                ("gemini", "not configured"),
                ("openrouter", "not configured"),
            ]
        finally:
            self._restore(snap)

    def test_finds_plugin_manifest_via_walk_up(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = _make_plugin_layout(
            tmp_path,
            user_config={"provider_openai": {"type": "string"}},
        )
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status(start_path=server_path)
            assert [name for name, _ in result] == ["openai"]
        finally:
            self._restore(snap)

    def test_no_manifest_and_no_state_yields_empty_list(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = tmp_path / "src" / "ask_another" / "server.py"
        server_path.parent.mkdir(parents=True)
        server_path.write_text("# stub")
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            assert _provider_status(start_path=server_path) == []
        finally:
            self._restore(snap)

    def test_malformed_manifest_yields_empty(
        self, tmp_path: Path, monkeypatch
    ):
        (tmp_path / "manifest.json").write_text("{ not valid json")
        server_path = tmp_path / "src" / "ask_another" / "server.py"
        server_path.parent.mkdir(parents=True)
        server_path.write_text("# stub")
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            assert _provider_status(start_path=server_path) == []
        finally:
            self._restore(snap)

    def test_missing_user_config_yields_empty(
        self, tmp_path: Path, monkeypatch
    ):
        (tmp_path / "manifest.json").write_text(json.dumps({"name": "x"}))
        server_path = tmp_path / "src" / "ask_another" / "server.py"
        server_path.parent.mkdir(parents=True)
        server_path.write_text("# stub")
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            assert _provider_status(start_path=server_path) == []
        finally:
            self._restore(snap)

    def test_preserves_declaration_order(self, tmp_path: Path, monkeypatch):
        server_path = _make_mcpb_layout(
            tmp_path,
            user_config={
                "provider_zeta": {"type": "string"},
                "provider_alpha": {"type": "string"},
                "provider_mike": {"type": "string"},
            },
        )
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status(start_path=server_path)
            assert [name for name, _ in result] == ["zeta", "alpha", "mike"]
        finally:
            self._restore(snap)

    # --- Composition ---

    def test_declared_with_configured_and_not_configured(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = _make_mcpb_layout(
            tmp_path,
            user_config={
                "provider_openai": {"type": "string"},
                "provider_gemini": {"type": "string"},
                "provider_openrouter": {"type": "string"},
            },
        )
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {"openai": "sk-x", "gemini": "g-x"}
        ask_another_server._provider_errors = {}
        try:
            assert _provider_status(start_path=server_path) == [
                ("openai", "configured"),
                ("gemini", "configured"),
                ("openrouter", "not configured"),
            ]
        finally:
            self._restore(snap)

    def test_runtime_error_produces_error_form(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = _make_mcpb_layout(
            tmp_path,
            user_config={
                "provider_openai": {"type": "string"},
                "provider_gemini": {"type": "string"},
            },
        )
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {"openai": "sk-x", "gemini": "g-x"}
        ask_another_server._provider_errors = {"gemini": "Google API key is required."}
        try:
            assert _provider_status(start_path=server_path) == [
                ("openai", "configured"),
                ("gemini", "configured (error: Google API key is required.)"),
            ]
        finally:
            self._restore(snap)

    def test_ad_hoc_extras_appended_alphabetically(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = _make_mcpb_layout(
            tmp_path,
            user_config={"provider_openai": {"type": "string"}},
        )
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {
            "openai": "sk-x",
            "anthropic": "ak-x",
            "beta": "bk-x",
        }
        ask_another_server._provider_errors = {}
        try:
            assert _provider_status(start_path=server_path) == [
                ("openai", "configured"),
                ("anthropic", "configured"),
                ("beta", "configured"),
            ]
        finally:
            self._restore(snap)

    def test_errored_undeclared_provider_appears(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = tmp_path / "src" / "ask_another" / "server.py"
        server_path.parent.mkdir(parents=True)
        server_path.write_text("# stub")
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {"foo": "fk-x"}
        ask_another_server._provider_errors = {"foo": "bad key"}
        try:
            assert _provider_status(start_path=server_path) == [
                ("foo", "configured (error: bad key)")
            ]
        finally:
            self._restore(snap)

    def test_none_value_in_errors_does_not_trigger_error_form(
        self, tmp_path: Path, monkeypatch
    ):
        server_path = _make_mcpb_layout(
            tmp_path,
            user_config={"provider_openai": {"type": "string"}},
        )
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        snap = self._snapshot()
        ask_another_server._provider_registry = {"openai": "sk-x"}
        ask_another_server._provider_errors = {"openai": None}
        try:
            assert _provider_status(start_path=server_path) == [
                ("openai", "configured")
            ]
        finally:
            self._restore(snap)


class TestProvidersSectionInInstructions:
    """_build_instructions() renders _provider_status() output as a
    Providers: section between Purpose: and Howto:, and the old
    Unavailable Providers: block is gone."""

    def _snapshot(self):
        return (
            dict(ask_another_server._provider_registry),
            dict(ask_another_server._provider_errors),
        )

    def _restore(self, snap):
        registry, errors = snap
        ask_another_server._provider_registry = registry
        ask_another_server._provider_errors = errors

    def test_section_present_when_status_non_empty(self):
        snap = self._snapshot()
        try:
            with patch.object(
                ask_another_server,
                "_provider_status",
                return_value=[
                    ("openai", "configured"),
                    ("gemini", "not configured"),
                ],
            ):
                out = ask_another_server._build_instructions()
            assert "Providers:" in out
            assert "  - openai: configured" in out
            assert "  - gemini: not configured" in out
        finally:
            self._restore(snap)

    def test_section_omitted_when_status_empty(self):
        snap = self._snapshot()
        try:
            with patch.object(
                ask_another_server, "_provider_status", return_value=[]
            ):
                out = ask_another_server._build_instructions()
            assert "Providers:" not in out
        finally:
            self._restore(snap)

    def test_section_between_purpose_and_howto(self):
        snap = self._snapshot()
        try:
            with patch.object(
                ask_another_server,
                "_provider_status",
                return_value=[("openai", "configured")],
            ):
                out = ask_another_server._build_instructions()
            purpose_idx = out.index("Purpose:")
            providers_idx = out.index("Providers:")
            howto_idx = out.index("Howto:")
            assert purpose_idx < providers_idx < howto_idx
        finally:
            self._restore(snap)

    def test_old_unavailable_providers_block_is_gone(self):
        # Exercise the REAL _provider_status() while _provider_errors has
        # entries — confirms the old block no longer renders.
        snap = self._snapshot()
        ask_another_server._provider_registry = {"openai": "sk-x"}
        ask_another_server._provider_errors = {"openai": "auth failed"}
        try:
            out = ask_another_server._build_instructions()
            assert "Unavailable Providers:" not in out
        finally:
            self._restore(snap)

    def test_renders_error_form_from_status(self):
        snap = self._snapshot()
        try:
            with patch.object(
                ask_another_server,
                "_provider_status",
                return_value=[("gemini", "configured (error: bad key)")],
            ):
                out = ask_another_server._build_instructions()
            assert "  - gemini: configured (error: bad key)" in out
        finally:
            self._restore(snap)
