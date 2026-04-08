import io
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from bs4 import BeautifulSoup
from PIL import Image

from clue.plugin.helpers.email_render import filter_elements, process_eml, render

BAD_HTML = (Path(__file__).parent / "bad.html").read_text()
GOOD_HTML = (Path(__file__).parent / "good.html").read_text()

# Sample email for testing
SAMPLE_EMAIL = b"""From: sender@example.com
To: receiver@example.com
Subject: Test Email
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-Id: <test123@example.com>
Content-Type: text/plain; charset="utf-8"

This is a test email body.
"""


def test_filter_elements():
    assert filter_elements(BAD_HTML) == BeautifulSoup(GOOD_HTML, "html.parser").prettify()


@patch("clue.plugin.helpers.email_render.os.remove")
@patch("clue.plugin.helpers.email_render.imgkit")
def test_process_eml_simplified_mode(mock_imgkit, mock_remove):
    """Test process_eml with simplified mode (default)."""

    # Mock imgkit to create fake image files
    def create_fake_file(html, path, options):
        # Create actual image file using PIL
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (100, 100), color="white")
        img.save(path, "JPEG")

    mock_imgkit.from_string = MagicMock(side_effect=create_fake_file)

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = process_eml(SAMPLE_EMAIL, tmp_dir, mode="simplified")

        # Verify imgkit was called
        assert mock_imgkit.from_string.called
        # Verify simplified mode was used (should have created probe and final render for text body)
        assert mock_imgkit.from_string.call_count >= 2
        # Verify result exists
        assert result


@patch("clue.plugin.helpers.email_render.os.remove")
@patch("clue.plugin.helpers.email_render.imgkit")
def test_process_eml_full_mode(mock_imgkit, mock_remove):
    """Test process_eml with full mode."""

    # Mock imgkit to create fake image files
    def create_fake_file(html, path, options):
        # Create actual image file using PIL
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (100, 100), color="white")
        img.save(path, "JPEG")

    mock_imgkit.from_string = MagicMock(side_effect=create_fake_file)

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = process_eml(SAMPLE_EMAIL, tmp_dir, mode="full")

        # Verify imgkit was called
        assert mock_imgkit.from_string.called
        # Verify result exists
        assert result


@patch("clue.plugin.helpers.email_render.os.remove")
@patch("clue.plugin.helpers.email_render.Image")
@patch("clue.plugin.helpers.email_render.imgkit")
def test_process_eml_simplified_mode_with_overflow(mock_imgkit, mock_image, mock_remove):
    """Test simplified mode detects overflow and adds truncation banner."""

    def create_fake_file(html, path, options):
        # Create actual image file using PIL
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (100, 100), color="white")
        img.save(path, "JPEG")

    mock_imgkit.from_string = MagicMock(side_effect=create_fake_file)

    # Mock probe image with width exceeding viewport
    probe_img = Mock()
    probe_img.size = (3000, 768)  # Wider than 2048px viewport
    probe_img.__enter__ = Mock(return_value=probe_img)
    probe_img.__exit__ = Mock(return_value=False)

    # Track calls to Image.open to return different values
    real_image_open = Image.open
    call_count = [0]

    def mock_open(path):
        call_count[0] += 1
        if call_count[0] == 1:  # First call is the probe
            return probe_img
        else:
            # For other calls, use real PIL
            return real_image_open(path)

    mock_image.open = mock_open
    mock_image.new = Image.new

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = process_eml(SAMPLE_EMAIL, tmp_dir, mode="simplified")

        # Check that truncation banner was included in the HTML
        calls = mock_imgkit.from_string.call_args_list
        # Find the render call for the text body (not the header)
        truncation_found = False
        for call in calls:
            html_content = call[0][0]
            if "Content truncated" in html_content or "Contenu tronqué" in html_content:
                truncation_found = True
                break
        assert truncation_found, "Truncation banner should be present in the rendered HTML"


@patch("clue.plugin.helpers.email_render.os.remove")
@patch("clue.plugin.helpers.email_render.Image")
@patch("clue.plugin.helpers.email_render.imgkit")
def test_process_eml_decompression_bomb_handling(mock_imgkit, mock_image, mock_remove):
    """Test that DecompressionBombError is caught and placeholder is created."""

    def create_fake_file(html, path, options):
        # Create actual image file using PIL
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (100, 100), color="white")
        img.save(path, "JPEG")

    mock_imgkit.from_string = MagicMock(side_effect=create_fake_file)

    # Track calls to Image.open
    real_image_open = Image.open
    call_count = [0]

    def mock_open(path):
        call_count[0] += 1
        # Simulate decompression bomb on the third call (after header open and probe in simplified mode)
        if call_count[0] == 3:
            raise Image.DecompressionBombError("Image size exceeds limit")
        else:
            return real_image_open(path)

    mock_image.open = mock_open
    mock_image.new = Image.new
    mock_image.DecompressionBombError = Image.DecompressionBombError

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = process_eml(SAMPLE_EMAIL, tmp_dir, mode="simplified")

        # Verify placeholder HTML was created
        calls = mock_imgkit.from_string.call_args_list
        placeholder_call_found = False
        for call in calls:
            html_content = call[0][0]
            if "Component Too Large" in html_content or "Composant trop volumineux" in html_content:
                placeholder_call_found = True
                break

        assert placeholder_call_found, "Placeholder HTML should be created for decompression bomb"


@patch("clue.plugin.helpers.email_render.os.remove")
@patch("clue.plugin.helpers.email_render.imgkit")
@patch("clue.plugin.helpers.email_render.unpack_stream")
def test_render_with_mode_simplified(mock_unpack, mock_imgkit, mock_remove):
    """Test render function with simplified mode."""

    def create_fake_file(html, path, options):
        # Create actual image file using PIL
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (100, 100), color="white")
        img.save(path, "JPEG")

    mock_imgkit.from_string = MagicMock(side_effect=create_fake_file)

    # Mock unpack_stream to write sample email
    def unpack_side_effect(cart_buffer, buf):
        buf.write(SAMPLE_EMAIL)

    mock_unpack.side_effect = unpack_side_effect

    cart_buffer = io.BytesIO(b"fake carted data")
    result = render("test.eml", cart_buffer, mode="simplified")

    # Verify the function completed successfully
    assert result is not None
    assert mock_imgkit.from_string.called


@patch("clue.plugin.helpers.email_render.os.remove")
@patch("clue.plugin.helpers.email_render.imgkit")
@patch("clue.plugin.helpers.email_render.unpack_stream")
def test_render_with_mode_full(mock_unpack, mock_imgkit, mock_remove):
    """Test render function with full mode."""

    def create_fake_file(html, path, options):
        # Create actual image file using PIL
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (100, 100), color="white")
        img.save(path, "JPEG")

    mock_imgkit.from_string = MagicMock(side_effect=create_fake_file)

    # Mock unpack_stream to write sample email
    def unpack_side_effect(cart_buffer, buf):
        buf.write(SAMPLE_EMAIL)

    mock_unpack.side_effect = unpack_side_effect

    cart_buffer = io.BytesIO(b"fake carted data")
    result = render("test.eml", cart_buffer, mode="full")

    # Verify the function completed successfully
    assert result is not None
    assert mock_imgkit.from_string.called
