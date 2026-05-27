# Provider Status Block Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified `Providers:` section to the MCP server's opening instructions that lists every provider we know anything about with one of three status strings (`configured`, `not configured`, `configured (error: …)`), so silent loss of an API key and runtime auth failures are both visible at session start. Replaces the existing `Unavailable Providers:` block.

**Architecture:** One helper, one rendering site. `_provider_status(start_path=None)` in `src/ask_another/server.py` walks up from the server file to find either `manifest.json` (MCPB bundle) or `.claude-plugin/plugin.json` (Claude Code plugin), reads declared provider names from `user_config`, then composes them with the existing `_provider_registry` and `_provider_errors` module state into a `list[tuple[str, str]]` of `(name, status)` pairs. Manifest-undeclared providers that appear in registry/errors are appended alphabetically. `_build_instructions()` calls `_provider_status()` and renders a `Providers:` section between `Purpose:` and `Howto:`; the existing `Unavailable Providers:` block is removed.

**Tech Stack:** Python 3.10+, pytest with `tmp_path` (built-in) for file-layout tests and `unittest.mock.patch` for monkeypatching. No new dependencies. All required imports (`Path`, `json`, `logging`) are already in `src/ask_another/server.py`.

**Spec:** [`docs/specs/2026-05-27-provider-status-block-design.md`](../specs/2026-05-27-provider-status-block-design.md)

---

### Task 0: Pre-flight check

**Files:** none

- [ ] **Step 1: Confirm clean working tree on `main`**

Run: `git status`
Expected: `On branch main` and `nothing to commit, working tree clean`. If not clean, stash or commit pending work before proceeding.

- [ ] **Step 2: Confirm the test suite is green before any changes**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: all tests pass. If anything is failing on `main`, stop and investigate — don't compound it.

---

### Task 1: Implement the whole feature in one TDD cycle

**Files:**
- Modify: `tests/test_provider_config.py` (append two new test classes at end)
- Modify: `src/ask_another/server.py` (add `_provider_status()` after `_load_config()` around line 340; modify `_build_instructions()` to insert new section ~line 771 and delete old block ~lines 849–853)

Write every test first, see them all fail, then make the changes that turn the whole suite green. One commit covers the helper, the new section, and the removal of the old block — that's the atomic unit of work.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_provider_config.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch

from ask_another import server as ask_another_server
from ask_another.server import _provider_status


def _make_manifest_layout(
    tmp_path: Path, *, user_config: dict | None = None, plugin_layout: bool = False
) -> Path:
    """Create a fake project tree under tmp_path with a manifest and a
    stub server.py. Returns the path to the stub server.py."""
    manifest = {"user_config": user_config} if user_config is not None else {}
    if plugin_layout:
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
    else:
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    server_path = tmp_path / "src" / "ask_another" / "server.py"
    server_path.parent.mkdir(parents=True)
    server_path.write_text("# stub")
    return server_path


class TestProviderStatus:
    """_provider_status() walks the plugin manifest and composes the
    declared list with the runtime _provider_registry and _provider_errors
    into deterministic (name, status_string) pairs."""

    def _snapshot(self):
        return (
            dict(ask_another_server._provider_registry),
            dict(ask_another_server._provider_errors),
        )

    def _restore(self, snap):
        registry, errors = snap
        ask_another_server._provider_registry = registry
        ask_another_server._provider_errors = errors

    # --- Manifest discovery behavior ---

    def test_finds_mcpb_manifest(self, tmp_path: Path):
        server_path = _make_manifest_layout(
            tmp_path,
            user_config={
                "provider_openai": {"type": "string"},
                "provider_gemini": {"type": "string"},
                "provider_openrouter": {"type": "string"},
                "zero_data_retention": {"type": "boolean"},
            },
        )
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

    def test_finds_claude_code_plugin_manifest(self, tmp_path: Path):
        server_path = _make_manifest_layout(
            tmp_path,
            user_config={
                "provider_openai": {"type": "string"},
                "provider_gemini": {"type": "string"},
            },
            plugin_layout=True,
        )
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status(start_path=server_path)
            assert [name for name, _ in result] == ["openai", "gemini"]
        finally:
            self._restore(snap)

    def test_no_manifest_and_no_state_yields_empty_list(self, tmp_path: Path):
        server_path = tmp_path / "src" / "ask_another" / "server.py"
        server_path.parent.mkdir(parents=True)
        server_path.write_text("# stub")
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            assert _provider_status(start_path=server_path) == []
        finally:
            self._restore(snap)

    def test_malformed_manifest_yields_empty(self, tmp_path: Path):
        (tmp_path / "manifest.json").write_text("{ not valid json")
        server_path = tmp_path / "src" / "ask_another" / "server.py"
        server_path.parent.mkdir(parents=True)
        server_path.write_text("# stub")
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            assert _provider_status(start_path=server_path) == []
        finally:
            self._restore(snap)

    def test_missing_user_config_yields_empty(self, tmp_path: Path):
        (tmp_path / "manifest.json").write_text(json.dumps({"name": "x"}))
        server_path = tmp_path / "src" / "ask_another" / "server.py"
        server_path.parent.mkdir(parents=True)
        server_path.write_text("# stub")
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            assert _provider_status(start_path=server_path) == []
        finally:
            self._restore(snap)

    def test_preserves_declaration_order(self, tmp_path: Path):
        server_path = _make_manifest_layout(
            tmp_path,
            user_config={
                "provider_zeta": {"type": "string"},
                "provider_alpha": {"type": "string"},
                "provider_mike": {"type": "string"},
            },
        )
        snap = self._snapshot()
        ask_another_server._provider_registry = {}
        ask_another_server._provider_errors = {}
        try:
            result = _provider_status(start_path=server_path)
            assert [name for name, _ in result] == ["zeta", "alpha", "mike"]
        finally:
            self._restore(snap)

    # --- Composition behavior ---

    def test_declared_with_configured_and_not_configured(self, tmp_path: Path):
        server_path = _make_manifest_layout(
            tmp_path,
            user_config={
                "provider_openai": {"type": "string"},
                "provider_gemini": {"type": "string"},
                "provider_openrouter": {"type": "string"},
            },
        )
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

    def test_runtime_error_produces_error_form(self, tmp_path: Path):
        server_path = _make_manifest_layout(
            tmp_path,
            user_config={
                "provider_openai": {"type": "string"},
                "provider_gemini": {"type": "string"},
            },
        )
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

    def test_ad_hoc_extras_appended_alphabetically(self, tmp_path: Path):
        server_path = _make_manifest_layout(
            tmp_path,
            user_config={"provider_openai": {"type": "string"}},
        )
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

    def test_errored_undeclared_provider_appears(self, tmp_path: Path):
        server_path = tmp_path / "src" / "ask_another" / "server.py"
        server_path.parent.mkdir(parents=True)
        server_path.write_text("# stub")
        snap = self._snapshot()
        ask_another_server._provider_registry = {"foo": "fk-x"}
        ask_another_server._provider_errors = {"foo": "bad key"}
        try:
            assert _provider_status(start_path=server_path) == [
                ("foo", "configured (error: bad key)")
            ]
        finally:
            self._restore(snap)

    def test_none_value_in_errors_does_not_trigger_error_form(self, tmp_path: Path):
        server_path = _make_manifest_layout(
            tmp_path,
            user_config={"provider_openai": {"type": "string"}},
        )
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

- [ ] **Step 2: Run the new tests and confirm they all fail**

Run: `uv run --with pytest python -m pytest tests/test_provider_config.py::TestProviderStatus tests/test_provider_config.py::TestProvidersSectionInInstructions -v`
Expected: All tests FAIL — most with `ImportError: cannot import name '_provider_status'`, the `TestProvidersSectionInInstructions` cases with `AssertionError` (either `Providers:` not found, or `Unavailable Providers:` still present).

- [ ] **Step 3: Add `_provider_status()` to `src/ask_another/server.py`**

Insert the following function immediately after `_load_config()` ends (around line 340, before the `# Model discovery` section divider):

```python
def _provider_status(
    start_path: Path | None = None, *, max_levels: int = 5
) -> list[tuple[str, str]]:
    """Return (name, status_string) pairs for every known provider.

    Walks the plugin manifest from ``start_path`` (default: this file)
    to discover declared providers, then composes that list with
    ``_provider_registry`` and ``_provider_errors`` into a deterministic
    list. Declared providers come first in manifest order; ad-hoc
    extras (in registry or errors but not declared) are appended
    alphabetically. Status is one of:

        - ``not configured`` — absent from ``_provider_registry``
        - ``configured`` — in registry, no non-None error recorded
        - ``configured (error: <msg>)`` — in registry, non-None entry
          in ``_provider_errors``
    """
    if start_path is None:
        start_path = Path(__file__).resolve()

    # Phase 1: walk up looking for a plugin manifest.
    declared: tuple[str, ...] = ()
    current = start_path.parent if start_path.is_file() else start_path
    for _ in range(max_levels):
        manifest = next(
            (
                p
                for p in (
                    current / "manifest.json",
                    current / ".claude-plugin" / "plugin.json",
                )
                if p.is_file()
            ),
            None,
        )
        if manifest is not None:
            try:
                data = json.loads(manifest.read_text())
                user_config = data.get("user_config") or {}
                declared = tuple(
                    key[len("provider_"):]
                    for key in user_config
                    if key.startswith("provider_")
                )
            except (json.JSONDecodeError, OSError, AttributeError) as exc:
                logger.warning(
                    "Could not parse manifest %s: %s", manifest, exc
                )
            break
        if current.parent == current:
            break
        current = current.parent

    # Phase 2: compose with runtime state.
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

- [ ] **Step 4: Modify `_build_instructions()` to emit the new section**

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

The remainder of the function (the `Howto:` content lines, `Feedback:` block, and conditional Favourite/Top Rated/Recently Added sections) is unchanged — those subsequent `lines.append(...)` / `lines.extend(...)` calls continue to operate on the same `lines` list.

- [ ] **Step 5: Delete the old `Unavailable Providers:` block**

Still in `_build_instructions()`, find this block near the bottom (around lines 849–853):

```python
    errors = {p: err for p, err in _provider_errors.items() if err}
    if errors:
        lines.append("Unavailable Providers:")
        for provider, err in sorted(errors.items()):
            lines.append(f"  - {provider}: {err}")
```

Delete those lines entirely. The new `Providers:` section now subsumes it.

- [ ] **Step 6: Run the new tests and confirm they pass**

Run: `uv run --with pytest python -m pytest tests/test_provider_config.py::TestProviderStatus tests/test_provider_config.py::TestProvidersSectionInInstructions -v`
Expected: All tests PASS.

- [ ] **Step 7: Run the full provider-config test file**

Run: `uv run --with pytest python -m pytest tests/test_provider_config.py -v`
Expected: All tests PASS (the new classes plus the existing `TestBareKeyFormat`, `TestLegacyPrefixedFormat`, `TestErrors`).

- [ ] **Step 8: Commit**

```bash
git add tests/test_provider_config.py src/ask_another/server.py
git commit -m "feat(server): unified Providers: status section in opening instructions"
```

---

### Task 2: Full-suite verification and live smoke test

**Files:** none

- [ ] **Step 1: Run the full test suite**

Run: `uv run --with pytest python -m pytest tests/ -v`
Expected: All tests PASS. No regressions outside the files we modified.

- [ ] **Step 2: Eyeball the live instructions output**

Run a quick check against the real manifest at the project root:

```bash
PROVIDER_OPENAI="sk-test-fake" uv run python -c "from ask_another.server import _build_instructions; print(_build_instructions())"
```

Expected: Output includes a `Providers:` section between `Purpose:` and `Howto:`, listing every provider declared in the project's `manifest.json`. The provider corresponding to `PROVIDER_OPENAI` shows `configured`; others show `not configured`. There is **no** `Unavailable Providers:` section in the output.

- [ ] **Step 3: Confirm working tree is clean**

Run: `git status`
Expected: `nothing to commit, working tree clean`.
