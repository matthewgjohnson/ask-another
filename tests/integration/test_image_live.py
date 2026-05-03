"""Live image generation tests — one per LiteLLM path.

The dedicated-API path (gpt-image-1) and the native completion path
(gemini-*-image) take different code routes through generate_image, so
each is exercised once. Images are saved to a tmp dir, not ~/Pictures.

These tests cost a few cents per run. Skip via -k 'not image' if needed.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from mcp.types import ImageContent, TextContent

import ask_another.server as server

pytestmark = pytest.mark.integration


@pytest.fixture
def image_tmp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect saved images to a tmp dir so test runs don't pollute ~/Pictures."""
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(tmp_path))
    return tmp_path


def _assert_image_block(blocks: list, tmp_dir: Path) -> None:
    images = [b for b in blocks if isinstance(b, ImageContent)]
    assert images, f"No ImageContent in result: {blocks}"
    assert images[0].data, "ImageContent has empty base64 data"
    saved = list(tmp_dir.glob("*"))
    assert saved, f"No image saved to {tmp_dir}"
    assert saved[0].stat().st_size > 0, "Saved image file is empty"


def test_generate_image_dedicated_path(openai_key: str, image_tmp_dir: Path) -> None:
    """gpt-image-1 routes through litellm.image_generation()."""
    blocks = server.generate_image(
        model="openai/gpt-image-1",
        prompt="a single red dot on white background, minimal",
        size="1024x1024",
        quality="low",
    )
    _assert_image_block(blocks, image_tmp_dir)


def test_generate_image_native_path(gemini_key: str, image_tmp_dir: Path) -> None:
    """gemini-2.5-flash-image routes through litellm.completion(modalities=...)."""
    blocks = server.generate_image(
        model="gemini/gemini-2.5-flash-image",
        prompt="a single red dot on white background, minimal",
    )
    _assert_image_block(blocks, image_tmp_dir)
    # Native path may also include text — fine, just confirm the type
    assert any(isinstance(b, (TextContent, ImageContent)) for b in blocks)
