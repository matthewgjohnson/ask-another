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
