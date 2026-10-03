import io
import re

import pytest
from PIL import Image


def test_upload_image_returns_201_with_image_id_and_ocr_draft(client, png_bytes) -> None:
    resp = client.post("/api/uploads", files={"file": ("q.png", png_bytes, "image/png")})

    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == 201
    assert body["message"] == "created"
    data = body["data"]
    assert re.fullmatch(r"[0-9a-f]{32}", data["image_id"])
    assert data["image_url"] == f"/api/images/{data['image_id']}"
    assert data["ocr"] == {"status": "ok", "text": "识别出的题目", "message": None}


class ExplodingOcrEngine:
    def recognize(self, image_bytes: bytes):
        raise RuntimeError("model crashed")


def test_upload_still_succeeds_when_ocr_engine_raises(settings, png_bytes) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app(settings, ocr_engine=ExplodingOcrEngine())) as client:
        resp = client.post("/api/uploads", files={"file": ("q.png", png_bytes, "image/png")})

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["image_id"]
    assert data["ocr"] == {"status": "failed", "text": "", "message": "文字识别失败，请手动输入"}


def _gif_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("P", (10, 10)).save(buffer, format="GIF")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "content",
    [b"this is not an image", _gif_bytes()],
    ids=["not-an-image", "gif"],
)
def test_upload_unsupported_file_returns_415(client, content) -> None:
    resp = client.post("/api/uploads", files={"file": ("x.png", content, "image/png")})

    assert resp.status_code == 415
    assert resp.json() == {
        "code": 415,
        "message": "仅支持 JPG、PNG、WebP 格式的图片",
        "data": None,
    }


def test_upload_larger_than_limit_returns_413(settings) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    small_limit = settings.model_copy(update={"max_upload_mb": 1})
    too_big = b"0" * (1024 * 1024 + 1)

    with TestClient(create_app(small_limit)) as client:
        resp = client.post("/api/uploads", files={"file": ("big.png", too_big, "image/png")})

    assert resp.status_code == 413
    assert resp.json() == {"code": 413, "message": "图片不能超过 1 MB", "data": None}


def test_upload_without_file_field_returns_400(client) -> None:
    resp = client.post("/api/uploads", files={"wrong_field": ("a.png", b"x", "image/png")})

    assert resp.status_code == 400
    assert resp.json() == {"code": 400, "message": "请选择要上传的图片", "data": None}
