import base64

import pytest

from mimo_vision_mcp.image_loader import (
    ImageInputError,
    build_image_part,
    detect_mime,
    normalize_input,
    raw_base64_to_data_url,
    read_image_as_data_url,
)

PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


@pytest.mark.parametrize(
    "data, expected",
    [
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg"),
        (PNG_1x1, "image/png"),
        (b"GIF89a.........", "image/gif"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
        (b"BM\x00\x00\x00\x00\x00\x00\x00\x00", "image/bmp"),
    ],
)
def test_detect_mime(data, expected):
    assert detect_mime(data) == expected


def test_detect_mime_unknown():
    with pytest.raises(ImageInputError):
        detect_mime(b"\x00\x01\x02\x03")


def test_normalize_data_uri_passthrough():
    uri = "data:image/png;base64,AAAA"
    assert normalize_input(uri) == uri


def test_normalize_url_passthrough():
    url = "https://example.com/a.jpg"
    assert normalize_input(url) == url


def test_normalize_local_file(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(PNG_1x1)
    uri = normalize_input(str(f))
    assert uri.startswith("data:image/png;base64,")


def test_normalize_raw_base64():
    b64 = base64.b64encode(PNG_1x1).decode()
    uri = normalize_input(b64)
    assert uri.startswith("data:image/png;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == PNG_1x1


def test_normalize_missing_file():
    with pytest.raises(ImageInputError):
        normalize_input("C:/no/such/file.png")


def test_read_image_as_data_url_mime(tmp_path):
    f = tmp_path / "x.jpg"
    f.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")
    assert read_image_as_data_url(str(f)).startswith("data:image/jpeg;base64,")


def test_raw_base64_with_mime_prefix():
    b64 = base64.b64encode(PNG_1x1).decode()
    assert raw_base64_to_data_url(f"image/png;base64,{b64}").startswith("data:image/png;base64,")


def test_build_image_part():
    part = build_image_part("https://example.com/a.png", "high")
    assert part == {"type": "image_url", "image_url": {"url": "https://example.com/a.png", "detail": "high"}}


def test_build_image_part_ignores_bad_detail():
    part = build_image_part("data:image/png;base64,AAAA", "bogus")
    assert "detail" not in part["image_url"]
