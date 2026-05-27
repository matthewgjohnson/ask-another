# Provider Status Block Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified `Providers:` section to the MCP server's opening instructions that lists every provider we know anything about with one of three status strings (`configured`, `not configured`, `configured (error: …)`), so silent loss of an API key and runtime auth failures are both visible at session start. Replaces the existing `Unavailable Providers:` block.

**Architecture:** One helper, one rendering site, no launch-config changes. `_provider_status(manifest_path=None, start_path=None)` in `src/ask_another/server.py` resolves the plugin manifest via a three-step lookup (explicit `manifest_path` arg → `$CLAUDE_PLUGIN_ROOT` env var auto-exported by Claude Code → walk-up from `Path(__file__)` for MCPB / local dev), parses the manifest's `user_config` for declared providers, then composes them with the existing `_provider_registry` and `_provider_errors` module state into a `list[tuple[str, str]]` of `(name, status)` pairs. Manifest-undeclared providers that appear in registry/errors are appended alphabetically. `_build_instructions()` calls `_provider_status()` and renders a `Providers:` section between `Purpose:` and `Howto:`; the existing `Unavailable Providers:` block is removed.

**Tech Stack:** Python 3.10+, pytest with `tmp_path` (built-in) for file-layout tests and `unittest.mock.patch` / `monkeypatch` for state and env mutation. No new dependencies. All required imports (`Path`, `json`, `os`, `logging`) are already in `src/ask_another/server.py`.

**Spec:** [`docs/specs/2026-05-27-provider-status-block-design.md`](../specs/2026-05-27-provider-status-block-design.md)

---

### Task 0: Pre-flight check

**Files:** none

- [ ] **Step 1: Confirm clean working tree on `main`**

Run: `git status`
Expected: `On branch main` and `nothing to commit, working tree clean`. If not clean, stash or commit pending work before proceeding.

- [ ] **Step 2: Confirm the test suite is green before any changes**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: all tests pass. If anything is failing on `main`, stop and investigate.

---

### Task 1: Implement the whole feature in one TDD cycle

**Files:**
- Modify: `tests/test_provider_config.py` (append two new test classes at end)
- Modify: `tests/test_provider_health.py` (update two existing tests at lines ~97 and ~190)
- Modify: `src/ask_another/server.py` (add `_provider_status()` after `_load_config()` ~line 340; insert new section in `_build_instructions()` ~line 771; delete old `Unavailable Providers:` block ~lines 849–853)

Write every test (new + updated) first, see them all fail, then make the changes that turn the whole suite green. One commit covers the helper, the new section, the removal of the old block, and the two updated tests.

- [ ] **Step 1: Write the new failing tests**

Append to `tests/test_provider_config.py`:

```python
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
```

- [ ] **Step 2: Update the two existing tests in `tests/test_provider_health.py`**

Open `tests/test_provider_health.py`. Find `test_build_instructions_shows_unavailable_providers` (around line 97) and replace its assertion block with the new expected shape:

```python
def test_build_instructions_shows_unavailable_providers(monkeypatch):
    """Instructions surface runtime errors via the unified Providers: section."""
    monkeypatch.setattr(server, "_provider_registry", {
        "openai": "sk-good",
        "gemini": "bad-key",
    })
    monkeypatch.setattr(server, "_provider_errors", {
        "openai": None,
        "gemini": "Google API key is required",
    })
    monkeypatch.setattr(server, "_annotations", {})
    instructions = server._build_instructions()
    assert "Providers:" in instructions
    assert "gemini: configured (error: Google API key is required)" in instructions
    assert "Unavailable Providers:" not in instructions
```

(Note: keep the function name as-is for git history continuity; the test now exercises the new section.)

Then find `test_full_flow_healthy_and_unhealthy` (around line 190) and replace its three trailing assertions on instructions with:

```python
    # Instructions filtered
    instructions = server._build_instructions()
    assert "openai/gpt-5.2" in instructions
    assert "gemini/gemini-3.1-pro" not in instructions
    assert "Providers:" in instructions
    assert "gemini: configured (error: API key invalid)" in instructions
    assert "Unavailable Providers:" not in instructions
```

- [ ] **Step 3: Run all new and updated tests and confirm they fail**

Run:
```
uv run --with pytest python -m pytest \
  tests/test_provider_config.py::TestProviderStatus \
  tests/test_provider_config.py::TestProvidersSectionInInstructions \
  tests/test_provider_health.py::test_build_instructions_shows_unavailable_providers \
  tests/test_provider_health.py::test_full_flow_healthy_and_unhealthy \
  -v
```
Expected: All tests FAIL — new-class tests with `ImportError: cannot import name '_provider_status'`, the section-presence and `Unavailable Providers:` removal assertions with `AssertionError`.

- [ ] **Step 4: Add `_provider_status()` to `src/ask_another/server.py`**

Insert immediately after `_load_config()` ends (around line 340, before the `# Model discovery` section divider):

```python
def _provider_status(
    manifest_path: Path | str | None = None,
    start_path: Path | None = None,
    *,
    max_levels: int = 5,
) -> list[tuple[str, str]]:
    """Return (name, status_string) pairs for every known provider.

    Locates the plugin manifest via a three-step lookup:
      1. ``manifest_path`` arg, if provided and the path exists
      2. ``$CLAUDE_PLUGIN_ROOT`` env var (auto-exported by Claude Code
         in plugin installs), checking ``.claude-plugin/plugin.json``
         then ``manifest.json`` under that root
      3. Walk up from ``start_path`` (default: this file) at most
         ``max_levels`` ancestors looking for ``manifest.json`` or
         ``.claude-plugin/plugin.json``

    Reads declared provider names from the manifest's ``user_config``
    (keys matching ``provider_*``, prefix stripped), then composes with
    ``_provider_registry`` and ``_provider_errors``. Declared providers
    come first in manifest order; ad-hoc extras (in registry or errors
    but not declared) are appended alphabetically. Status is one of:
    ``not configured``, ``configured``, or ``configured (error: <msg>)``.
    """
    resolved: Path | None = None

    # Lookup 1: explicit arg
    if manifest_path is not None:
        p = Path(manifest_path)
        if p.is_file():
            resolved = p

    # Lookup 2: CLAUDE_PLUGIN_ROOT
    if resolved is None:
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        if plugin_root:
            for candidate in (
                Path(plugin_root) / ".claude-plugin" / "plugin.json",
                Path(plugin_root) / "manifest.json",
            ):
                if candidate.is_file():
                    resolved = candidate
                    break

    # Lookup 3: walk up from start_path
    if resolved is None:
        if start_path is None:
            start_path = Path(__file__).resolve()
        current = start_path.parent if start_path.is_file() else start_path
        for _ in range(max_levels):
            for candidate in (
                current / "manifest.json",
                current / ".claude-plugin" / "plugin.json",
            ):
                if candidate.is_file():
                    resolved = candidate
                    break
            if resolved is not None:
                break
            if current.parent == current:
                break
            current = current.parent

    # Parse manifest for declared providers
    declared: tuple[str, ...] = ()
    if resolved is not None:
        try:
            data = json.loads(resolved.read_text())
            user_config = data.get("user_config") or {}
            declared = tuple(
                key[len("provider_"):]
                for key in user_config
                if key.startswith("provider_")
            )
        except (json.JSONDecodeError, OSError, AttributeError) as exc:
            logger.warning(
                "Could not parse manifest %s: %s", resolved, exc
            )

    # Compose with runtime state
    declared_set = set(declared)
    extras = sorted(
        (set(_provider_registry) | {p for p, e in _provider_errors.items() if e})
        - declared_set
    )
    out: list[tuple[str, str]] = []
    for name in list(declared) + extras:
        if name not in _provider_registry:
            status = "not configured"
        else:
            err = _provider_errors.get(name)
            status = f"configured (error: {err})" if err else "configured"
        out.append((name, status))
    return out
```

- [ ] **Step 5: Insert the new section in `_build_instructions()`**

In `_build_instructions()` (starts ~line 766), find the head of the function:

```python
    lines = [
        "Purpose:",
        "  - Ask another LLM for a second opinion.",
        "  - Provide access to other models through litellm.",
        "Howto:",
```

Replace with:

```python
    lines = [
        "Purpose:",
        "  - Ask another LLM for a second opinion.",
        "  - Provide access to other models through litellm.",
    ]
    statuses = _provider_status()
    if statuses:
        lines.append("Providers:")
        for name, status in statuses:
            lines.append(f"  - {name}: {status}")
    lines.append("Howto:")
```

- [ ] **Step 6: Delete the old `Unavailable Providers:` block**

Still in `_build_instructions()`, find this block near the bottom (around lines 849–853):

```python
    errors = {p: err for p, err in _provider_errors.items() if err}
    if errors:
        lines.append("Unavailable Providers:")
        for provider, err in sorted(errors.items()):
            lines.append(f"  - {provider}: {err}")
```

Delete those lines entirely.

- [ ] **Step 7: Run all new and updated tests and confirm they pass**

Run:
```
uv run --with pytest python -m pytest \
  tests/test_provider_config.py::TestProviderStatus \
  tests/test_provider_config.py::TestProvidersSectionInInstructions \
  tests/test_provider_health.py::test_build_instructions_shows_unavailable_providers \
  tests/test_provider_health.py::test_full_flow_healthy_and_unhealthy \
  -v
```
Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add tests/test_provider_config.py tests/test_provider_health.py src/ask_another/server.py
git commit -m "feat(server): unified Providers: status section in opening instructions"
```

---

### Task 2: Full-suite verification and live smoke test

**Files:** none

- [ ] **Step 1: Run the full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All tests PASS. The "probably safe" tests called out in the spec (4 in `test_annotations.py`, 1 in `test_provider_health.py::test_build_instructions_excludes_unhealthy_favourites`) should pass unchanged — if any fail, investigate before claiming completion.

- [ ] **Step 2: Eyeball the live instructions output**

Run a quick check against the real manifest at the project root:

```bash
PROVIDER_OPENAI="sk-test-fake" uv run python -c "from ask_another.server import _build_instructions; print(_build_instructions())"
```

Expected: Output includes a `Providers:` section between `Purpose:` and `Howto:`, listing every provider declared in the project's `manifest.json`. The provider corresponding to `PROVIDER_OPENAI` shows `configured`; others show `not configured`. There is **no** `Unavailable Providers:` section in the output.

- [ ] **Step 3: Confirm working tree is clean**

Run: `git status`
Expected: `nothing to commit, working tree clean`.
