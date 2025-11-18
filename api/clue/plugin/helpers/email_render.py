import base64
import email
import email.header
import io
import os
import quopri
import re
import tempfile
import textwrap
from email.errors import HeaderParseError
from email.message import Message
from tempfile import NamedTemporaryFile
from typing import cast

# TODO: Better handle these specific imports in dependency management
import imgkit
from bs4 import BeautifulSoup
from cart import unpack_stream
from PIL import Image

from clue.common.exceptions import ClueException, ClueRuntimeError
from clue.common.logging import get_logger
from clue.models.results.image import ImageResult

logger = get_logger(__file__)


TEXT_TYPES = ["text/plain", "text/html"]
IMAGE_TYPES = ["image/gif", "image/jpeg", "image/png"]


def append_images(images):
    "Concatenate images together"
    try:
        bg_color = (255, 255, 255)
        widths, heights = zip(*(i.size for i in images))

        new_width = max(widths)
        new_height = sum(heights)
        new_im = Image.new("RGB", (new_width, new_height), color=bg_color)
        offset = 0
        for im in images:
            x = 0
            new_im.paste(im, (x, offset))
            offset += im.size[1]
        return new_im
    except Exception as e:
        raise ClueException("Error when appending images") from e


def get_header_data(msg: Message, header: str) -> str:
    "Decode the value of a given header"
    try:
        decode = email.header.decode_header(msg[header])[0]

        if isinstance(decode[0], bytes):
            value = decode[0].decode()
        else:
            value = str(decode[0])
    except HeaderParseError:
        logger.warning("Could not parse header [%s], defaulting to Unknown", header)
        value = "&lt;Unknown&gt;"
    logger.info("%s: %s", header, value)
    return value.replace("<", "&lt;").replace(">", "&gt;")


def filter_elements(payload: str) -> str:
    "Filter external links from html"
    logger.info("Performing trimming of external fonts/styles")
    soup = BeautifulSoup(payload, "html.parser")

    logger.debug("Checking for link elements")
    for link in soup.select("link"):
        logger.debug("Removing link tag: %s", link["href"])
        link.decompose()

    logger.debug("Checking for style elements with imports")
    for style in soup.select("style"):
        if style.string and "@import" in style.string:
            _import_match = re.search(r"(@import.+;)", style.string)
            if _import_match:
                logger.debug("Removing import: %s", _import_match.group(1))
            style.string = re.sub(r"@import.+;", "", style.string).strip()

            if not style.string:
                style.decompose()

    logger.debug("Checking for script tags")
    for script in soup.select("script"):
        logger.debug("Removing script")
        script.decompose()

    return cast(str, soup.prettify())


def process_eml(data, output_dir, load_images=False):  # noqa: C901
    "Process the email (bytes), extract MIME parts and useful headers. Generate a JPEG picture of the mail"
    logger.debug("Beginning eml processing")

    try:
        msg = email.message_from_bytes(data)
        date_field = get_header_data(msg, "Date")
        from_field = get_header_data(msg, "From")
        to_field = get_header_data(msg, "To")
        subject_field = get_header_data(msg, "Subject")
        id_field = get_header_data(msg, "Message-Id")

        imgkit_options = {"load-error-handling": "skip", "no-images": None}

        images_list = []

        # Build a first image with basic mail details
        headers = textwrap.dedent(f"""
        <table width="100%%">
            <tr><td align="right"><b>Date:</b></td><td>{date_field}</td></tr>
            <tr><td align="right"><b>From:</b></td><td>{from_field}</td></tr>
            <tr><td align="right"><b>To:</b></td><td>{to_field}</td></tr>
            <tr><td align="right"><b>Subject:</b></td><td>{subject_field}</td></tr>
            <tr><td align="right"><b>Message-Id:</b></td><td>{id_field}</td></tr>
        </table>
        <hr></p>
        """)

        try:
            header_path = NamedTemporaryFile(suffix=".jpeg").name
            imgkit.from_string(headers, header_path, options=imgkit_options)
            logger.info("Created headers: %s", header_path)
            images_list.append(header_path)
        except Exception:
            logger.exception("Creation of headers failed.")

        #
        # Main loop - process the MIME parts
        #
        for part in msg.walk():
            mime_type = part.get_content_type()
            if part.is_multipart():
                logger.info("Multipart found, continue")
                continue

            logger.info("Found MIME part: %s" % mime_type)
            if mime_type in TEXT_TYPES:
                try:
                    # Fix formatting
                    payload = part.get_payload(decode=True)
                    payload = re.sub(rb"(\r\n){1,}", b"\r\n", payload)  # type: ignore[arg-type]
                    payload = payload.replace(b"\r\n", b"<br>")
                    payload = re.sub(rb"(<br> ){2,}", b"<br><br>", payload)

                    payload = quopri.decodestring(payload).decode("utf-8", errors="ignore")
                except Exception:
                    payload = str(quopri.decodestring(part.get_payload(decode=True)))[2:-1]  # type: ignore[arg-type]

                payload = filter_elements(payload)

                try:
                    payload_path = NamedTemporaryFile(suffix=".jpeg").name
                    imgkit.from_string(payload, payload_path, options=imgkit_options)
                    logger.info("Decoded %s" % payload_path)
                    images_list.append(payload_path)
                except Exception as e:
                    logger.warning(f"Decoding this MIME part returned error: {e}")

            elif mime_type in IMAGE_TYPES and load_images:
                payload = part.get_payload(decode=False)
                payload_path = NamedTemporaryFile(suffix=".jpeg").name
                imgdata = base64.b64decode(payload)  # type: ignore[arg-type]
                try:
                    with open(payload_path, "wb") as f:
                        f.write(imgdata)
                    logger.info("Decoded %s" % payload_path)
                    images_list.append(payload_path)
                except Exception as e:
                    logger.warning(f"Decoding this MIME part returned error: {e}")

        result_image = os.path.join(output_dir, "output.jpeg")
        if len(images_list) > 0:
            images = [img.convert("RGB") if img.mode != "RGB" else img for img in map(Image.open, images_list)]
            combo = append_images(images)
            combo.save(result_image)
            # Clean up temporary images
            for i in images_list:
                os.remove(i)
            return result_image
        else:
            return False
    except Exception as e:
        logger.exception("Exception when processing eml")
        raise ClueException("Error when processing email") from e


def render(email_path: str, cart_buffer: io.BytesIO) -> ImageResult | None:
    "Helper function that, given a buffer containing a carted email, returns an image rendering of it."
    cart_buffer.seek(0)
    buf = io.BytesIO()
    unpack_stream(cart_buffer, buf)
    buf.seek(0)

    logger.debug("Initializing temporary directory")
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger.debug("Temporary directory initialized: %s", tmp_dir)

        process_eml(
            buf.read(),
            tmp_dir,
        )

        error = None
        if any("output" in s for s in os.listdir(tmp_dir)):
            previews = [s for s in os.listdir(tmp_dir) if "output" in s]
            if len(previews) == 0:
                error = "Target file couldn't be converted to image."
            elif len(previews) > 1:
                error = "Target file is generating multiple images."
        else:
            error = "Output file does not exist."

        if error:
            raise ClueRuntimeError(error)

        # There is only 1 rendered image
        with open(f"{tmp_dir}/{previews[0]}", "rb") as f:  # type: ignore
            return ImageResult(
                image=f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode("utf-8")}",
                alt=f"Rendering of {email_path}",
            )

    logger.warning("No image result generated - returning None")
