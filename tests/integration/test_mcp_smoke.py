"""MCP boot smoke tests — spawn the server the way Claude Desktop does.

These tests would have caught the "Could not attach to MCP server" failure:
they exercise the stdio handshake, FastMCP wiring, lifespan, and tool
registration that in-process function tests can't see.

Boot budget: 10 seconds. CDA's effective attach timeout is in this range,
and any longer means real users will hit timeouts on cold starts.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = pytest.mark.integration

BOOT_BUDGET_SECONDS = 10.0


def _fresh_annotations_file(tmp_path: Path) -> Path:
    """Write an annotations file with one fresh entry so the lifespan skips
    enrichment fetches (which would otherwise hit GitHub/HuggingFace and
    blow the boot budget on a cold network)."""
    now = datetime.now(timezone.utc).isoformat()
    path = tmp_path / "annotations.json"
    path.write_text(json.dumps({
        "openai/gpt-5.2": {
            "metadata": {"last_updated": now, "first_seen": now},
        }
    }))
    return path


def _server_params(annotations_file: Path, extra_env: dict[str, str] | None = None) -> StdioServerParameters:
    """Spawn the server via the same Python interpreter running the tests."""
    env = {
        "PATH": os.environ["PATH"],
        "ANNOTATIONS_FILE": str(annotations_file),
        "CACHE_TTL_MINUTES": "999999",  # never refresh during the test
    }
    # Forward provider keys if they're set, so tool calls can succeed
    for k, v in os.environ.items():
        if k.startswith("PROVIDER_"):
            env[k] = v
    if extra_env:
        env.update(extra_env)

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "ask_another.server"],
        env=env,
    )


@pytest.mark.anyio
async def test_server_boots_within_budget(tmp_path: Path) -> None:
    """The server completes MCP initialize within CDA's attach window."""
    params = _server_params(_fresh_annotations_file(tmp_path))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            with anyio.fail_after(BOOT_BUDGET_SECONDS):
                await session.initialize()


@pytest.mark.anyio
async def test_server_registers_all_tools(tmp_path: Path) -> None:
    """Every tool documented in CLAUDE.md is registered with FastMCP."""
    expected = {
        "search_families",
        "search_models",
        "completion",
        "annotate_models",
        "refresh_models",
        "feedback",
        "start_research",
        "check_research",
        "cancel_research",
        "generate_image",
    }
    params = _server_params(_fresh_annotations_file(tmp_path))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            with anyio.fail_after(BOOT_BUDGET_SECONDS):
                await session.initialize()
            tools = await session.list_tools()
    names = {t.name for t in tools.tools}
    missing = expected - names
    assert not missing, f"Tools missing from registration: {missing}"


@pytest.mark.anyio
async def test_server_boots_with_stale_annotations(tmp_path: Path) -> None:
    """Cold-start case: empty annotations file triggers enrichment in the
    lifespan, which currently BLOCKS the lifespan yield — meaning MCP
    `initialize` waits for enrichment to complete.

    On a fast network this is ~5-10s. On slow networks it can blow past
    30s, at which point CDA times out and shows "Could not attach to MCP
    server" — exactly the failure observed in production.

    The right fix is to run enrichment as a background task in the lifespan
    so the server responds to MCP immediately. Until that lands, this test
    will fail intermittently on slow networks — which is the signal we
    want, not noise to hide.

    Budget is set to 15s deliberately: anything slower IS a production bug.
    """
    annotations = tmp_path / "annotations.json"
    annotations.write_text("{}")
    params = _server_params(annotations)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            with anyio.fail_after(15.0):
                await session.initialize()


@pytest.mark.anyio
async def test_server_handles_tool_call(tmp_path: Path) -> None:
    """A real tool call round-trips through the MCP transport.

    Uses `feedback` because it has no provider dependency — pure local
    file write — so this test runs without any PROVIDER_* keys set.
    """
    feedback_log = tmp_path / "feedback.jsonl"
    params = _server_params(
        _fresh_annotations_file(tmp_path),
        extra_env={"FEEDBACK_LOG": str(feedback_log)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            with anyio.fail_after(BOOT_BUDGET_SECONDS):
                await session.initialize()
            result = await session.call_tool(
                "feedback",
                {"issue": "smoke test", "tool_name": "test_mcp_smoke"},
            )
    assert result.content, "Tool call returned no content"
    assert feedback_log.exists(), "Tool call did not write to feedback log"
    entry = json.loads(feedback_log.read_text().strip())
    assert entry["issue"] == "smoke test"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
