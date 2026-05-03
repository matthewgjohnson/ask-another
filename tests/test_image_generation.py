"""Tests for the generate_image tool and its helpers."""

import base64
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import ask_another.server as server


# ---------------------------------------------------------------------------
# _is_native_image_model
# ---------------------------------------------------------------------------


def test_native_image_model_gemini_flash():
    assert server._is_native_image_model("gemini/gemini-2.5-flash-image") is True


def test_native_image_model_gemini_pro():
    assert server._is_native_image_model("gemini/gemini-3-pro-image-preview") is True


def test_native_image_model_gemini_31():
    assert server._is_native_image_model("gemini/gemini-3.1-flash-image-preview") is True


def test_native_image_model_openrouter_gemini():
    assert server._is_native_image_model("openrouter/google/gemini-3.1-flash-image-preview") is True


def test_not_native_image_model_gpt():
    assert server._is_native_image_model("openai/gpt-image-1") is False


def test_not_native_image_model_dalle():
    assert server._is_native_image_model("openai/dall-e-3") is False


def test_not_native_image_model_imagen():
    assert server._is_native_image_model("gemini/imagen-4.0-generate-001") is False


# ---------------------------------------------------------------------------
# _extract_image_b64
# ---------------------------------------------------------------------------


def test_extract_from_b64_json():
    raw_b64 = base64.b64encode(b"fake-png-data").decode()
    data, mime = server._extract_image_b64(raw_b64, None)
    assert data == raw_b64
    assert mime == "image/png"


def test_extract_from_data_url():
    raw_b64 = base64.b64encode(b"fake-png-data").decode()
    data_url = f"data:image/webp;base64,{raw_b64}"
    data, mime = server._extract_image_b64(None, data_url)
    assert data == raw_b64
    assert mime == "image/webp"


def test_extract_raises_on_no_data():
    try:
        server._extract_image_b64(None, None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No image data" in str(e)


# ---------------------------------------------------------------------------
# _save_image
# ---------------------------------------------------------------------------


def test_save_image_creates_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(tmp_path))
    raw_bytes = b"fake-png-data"
    raw_b64 = base64.b64encode(raw_bytes).decode()

    filepath = server._save_image(raw_b64, "image/png", "a cute cat")

    assert filepath.exists()
    assert filepath.read_bytes() == raw_bytes
    assert filepath.suffix == ".png"
    assert "a-cute-cat" in filepath.name


def test_save_image_jpeg_extension(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(tmp_path))
    raw_b64 = base64.b64encode(b"fake-jpg-data").decode()

    filepath = server._save_image(raw_b64, "image/jpeg", "sunset")

    assert filepath.suffix == ".jpg"


def test_save_image_creates_directory(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "nested" / "dir"
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(output_dir))
    raw_b64 = base64.b64encode(b"data").decode()

    filepath = server._save_image(raw_b64, "image/png", "test")

    assert output_dir.exists()
    assert filepath.exists()


# ---------------------------------------------------------------------------
# generate_image — image_generation API path
# ---------------------------------------------------------------------------


def test_generate_image_via_image_generation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(tmp_path))

    raw_bytes = b"fake-image-bytes"
    raw_b64 = base64.b64encode(raw_bytes).decode()

    mock_img = SimpleNamespace(b64_json=raw_b64, url=None, revised_prompt=None)
    mock_response = SimpleNamespace(data=[mock_img])

    with patch.object(server, "_resolve_model", return_value=("openai/gpt-image-1", "sk-test")):
        with patch("litellm.image_generation", return_value=mock_response) as mock_call:
            result = server.generate_image(
                model="openai/gpt-image-1",
                prompt="a cat on a robot",
            )

    mock_call.assert_called_once()
    kwargs = mock_call.call_args[1]
    assert kwargs["model"] == "openai/gpt-image-1"
    assert kwargs["n"] == 1

    # Should return ImageContent + TextContent (saved path)
    assert len(result) == 2
    assert result[0].type == "image"
    assert result[0].data == raw_b64
    assert result[0].mimeType == "image/png"
    assert result[1].type == "text"
    assert "Saved to:" in result[1].text


def test_generate_image_with_revised_prompt(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(tmp_path))

    raw_b64 = base64.b64encode(b"data").decode()
    mock_img = SimpleNamespace(b64_json=raw_b64, url=None, revised_prompt="A detailed cat")
    mock_response = SimpleNamespace(data=[mock_img])

    with patch.object(server, "_resolve_model", return_value=("openai/gpt-image-1", "sk-test")):
        with patch("litellm.image_generation", return_value=mock_response):
            result = server.generate_image(
                model="openai/gpt-image-1",
                prompt="cat",
            )

    assert len(result) == 3
    assert result[0].type == "text"
    assert "Revised prompt:" in result[0].text
    assert result[1].type == "image"
    assert result[2].type == "text"


def test_generate_image_passes_size_and_quality(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(tmp_path))

    raw_b64 = base64.b64encode(b"data").decode()
    mock_img = SimpleNamespace(b64_json=raw_b64, url=None, revised_prompt=None)
    mock_response = SimpleNamespace(data=[mock_img])

    with patch.object(server, "_resolve_model", return_value=("openai/gpt-image-1", "sk-test")):
        with patch("litellm.image_generation", return_value=mock_response) as mock_call:
            server.generate_image(
                model="openai/gpt-image-1",
                prompt="cat",
                size="1536x1024",
                quality="hd",
            )

    kwargs = mock_call.call_args[1]
    assert kwargs["size"] == "1536x1024"
    assert kwargs["quality"] == "hd"


# ---------------------------------------------------------------------------
# generate_image — completion with modalities path
# ---------------------------------------------------------------------------


def test_generate_image_via_completion(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(tmp_path))

    raw_bytes = b"fake-image-bytes"
    raw_b64 = base64.b64encode(raw_bytes).decode()
    data_url = f"data:image/png;base64,{raw_b64}"

    mock_message = SimpleNamespace(
        content="Here is your image:",
        images=[{"image_url": {"url": data_url}}],
    )
    mock_choice = SimpleNamespace(message=mock_message)
    mock_response = SimpleNamespace(choices=[mock_choice])

    with patch.object(server, "_resolve_model", return_value=("gemini/gemini-2.5-flash-image", "gk-test")):
        with patch("litellm.completion", return_value=mock_response) as mock_call:
            result = server.generate_image(
                model="gemini/gemini-2.5-flash-image",
                prompt="a sunset diagram",
            )

    mock_call.assert_called_once()
    kwargs = mock_call.call_args[1]
    assert kwargs["modalities"] == ["image", "text"]

    # Text content + ImageContent + saved path
    assert len(result) == 3
    assert result[0].type == "text"
    assert result[0].text == "Here is your image:"
    assert result[1].type == "image"
    assert result[1].data == raw_b64
    assert result[2].type == "text"
    assert "Saved to:" in result[2].text


def test_generate_image_completion_no_images(monkeypatch):
    mock_message = SimpleNamespace(content="Sorry, I cannot generate images.", images=[])
    mock_choice = SimpleNamespace(message=mock_message)
    mock_response = SimpleNamespace(choices=[mock_choice])

    with patch.object(server, "_resolve_model", return_value=("gemini/gemini-2.5-flash-image", "gk-test")):
        with patch("litellm.completion", return_value=mock_response):
            try:
                server.generate_image(
                    model="gemini/gemini-2.5-flash-image",
                    prompt="test",
                )
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "returned no images" in str(e)


def test_make_inline_preview_passes_through_small_image():
    """Small images skip resize and return unchanged."""
    raw = b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000  # not a real PNG, but small
    b64 = base64.b64encode(raw).decode()
    out_b64, out_mime, resized = server._make_inline_preview(b64, "image/png")
    assert out_b64 == b64
    assert out_mime == "image/png"
    assert resized is False


def _noisy_image(size: tuple[int, int], mode: str = "RGB") -> bytes:
    """Generate a PNG of incompressible noise so we exceed the size budget."""
    from io import BytesIO
    import os as _os
    from PIL import Image

    pixel_count = size[0] * size[1] * (4 if mode == "RGBA" else 3)
    img = Image.frombytes(mode, size, _os.urandom(pixel_count))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_make_inline_preview_resizes_large_image():
    """An image whose b64 exceeds the budget is downsized and re-encoded as JPEG."""
    from io import BytesIO
    from PIL import Image

    raw = _noisy_image((1024, 1024))
    big_b64 = base64.b64encode(raw).decode()
    assert len(big_b64) > server._INLINE_IMAGE_MAX_B64_BYTES, "test image not big enough"

    out_b64, out_mime, resized = server._make_inline_preview(big_b64, "image/png")
    assert resized is True
    assert out_mime == "image/jpeg"
    assert len(out_b64) < server._INLINE_IMAGE_MAX_B64_BYTES
    out_img = Image.open(BytesIO(base64.b64decode(out_b64)))
    assert max(out_img.size) <= server._INLINE_PREVIEW_MAX_DIM


def test_make_inline_preview_handles_alpha_channel():
    """RGBA images flatten onto white before JPEG encoding (no crash)."""
    from io import BytesIO
    from PIL import Image

    raw = _noisy_image((1024, 1024), mode="RGBA")
    big_b64 = base64.b64encode(raw).decode()
    assert len(big_b64) > server._INLINE_IMAGE_MAX_B64_BYTES, "test image not big enough"

    out_b64, out_mime, resized = server._make_inline_preview(big_b64, "image/png")
    assert resized is True
    assert out_mime == "image/jpeg"
    out_img = Image.open(BytesIO(base64.b64decode(out_b64)))
    assert out_img.mode == "RGB"


def test_generate_image_completion_no_choices(monkeypatch):
    """Empty choices list (e.g. safety filter) raises ValueError, not IndexError."""
    mock_response = SimpleNamespace(choices=[])

    with patch.object(server, "_resolve_model", return_value=("gemini/gemini-2.5-flash-image", "gk-test")):
        with patch("litellm.completion", return_value=mock_response):
            try:
                server.generate_image(
                    model="gemini/gemini-2.5-flash-image",
                    prompt="test",
                )
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "no response choices" in str(e)
            except IndexError:
                assert False, "Bug regression: IndexError instead of ValueError"
