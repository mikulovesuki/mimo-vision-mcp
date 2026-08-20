"""Normalize image inputs (local path / URL / data URI / raw base64) to OpenAI-compatible content."""

import base64
from pathlib import Path
from urllib.parse import urlparse

_JPEG_SIG = b"\xff\xd8\xff"
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_GIF_SIG = b"GIF8"
_WEBP_SIG = b"RIFF"
_BMP_SIG = b"BM"

MAX_BASE64_BYTES = 50 * 1024 * 1024  # 50 MB API limit

ALLOWED_FORMATS = ("jpg", "jpeg", "png", "gif", "webp", "bmp")


class ImageInputError(ValueError):
    """Raised when an image input cannot be interpreted."""


def detect_mime(data: bytes) -> str:
    """Detect MIME type from image magic bytes."""
    if data.startswith(_PNG_SIG):
        return "image/png"
    if data.startswith(_JPEG_SIG):
        return "image/jpeg"
    if data.startswith(_GIF_SIG):
        return "image/gif"
    if data.startswith(_BMP_SIG):
        return "image/bmp"
    if data.startswith(_WEBP_SIG) and data[8:12] == b"WEBP":
        return "image/webp"
    raise ImageInputError("无法识别图片格式（支持 JPEG/PNG/GIF/WebP/BMP）")


def is_url(value: str) -> bool:
    return urlparse(value).scheme in ("http", "https")


def is_data_uri(value: str) -> bool:
    return value.startswith("data:")


def read_image_as_data_url(path: str) -> str:
    """Read a local image file and return it as a base64 data URI."""
    p = Path(path)
    if not p.is_file():
        raise ImageInputError(f"本地图片文件不存在: {path}")
    data = p.read_bytes()
    if len(data) > MAX_BASE64_BYTES:
        raise ImageInputError(f"图片过大（>{MAX_BASE64_BYTES // (1024 * 1024)}MB）: {path}")
    mime = detect_mime(data)
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def raw_base64_to_data_url(value: str) -> str:
    """Wrap a raw base64 string into a data URI (MIME inferred if it has a prefix)."""
    if ";" in value and value.split(";")[0].startswith("image/"):
        # e.g. "image/png;base64,xxxx" without the leading data:
        mime, payload = value.split(";", 1)
        payload = payload.split(",", 1)[1] if payload.startswith("base64,") else payload
        return f"data:{mime};base64,{payload}"
    try:
        raw = base64.b64decode(value, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ImageInputError("无法解析该输入：既不是路径/URL，也不是合法的 base64 数据") from exc
    if len(raw) > MAX_BASE64_BYTES:
        raise ImageInputError("base64 图片数据超过 50MB 限制")
    mime = detect_mime(raw)
    return f"data:{mime};base64,{value}"


def normalize_input(value: str) -> str:
    """Convert one image input to a data URI (or pass through URL/data URI)."""
    value = (value or "").strip()
    if not value:
        raise ImageInputError("图片输入为空")
    if is_data_uri(value):
        return value
    if is_url(value):
        return value
    if Path(value).is_file():
        return read_image_as_data_url(value)
    return raw_base64_to_data_url(value)


def build_image_part(data_uri_or_url: str, detail: str | None = None) -> dict:
    """Build an OpenAI 'image_url' content part."""
    part = {"type": "image_url", "image_url": {"url": data_uri_or_url}}
    if detail in ("low", "high", "auto"):
        part["image_url"]["detail"] = detail
    return part


def build_responses_image_part(data_uri_or_url: str, detail: str | None = None) -> dict:
    """Build a Responses API 'input_image' content part."""
    part = {"type": "input_image", "image_url": data_uri_or_url}
    if detail in ("low", "high", "auto"):
        part["detail"] = detail
    return part
