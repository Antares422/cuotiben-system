from urllib.parse import quote

import pytest


def test_get_image_returns_original_bytes_with_content_type(client, png_bytes) -> None:
    uploaded = client.post("/api/uploads", files={"file": ("q.png", png_bytes, "image/png")})
    image_url = uploaded.json()["data"]["image_url"]

    resp = client.get(image_url)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == png_bytes


@pytest.mark.parametrize(
    "image_id",
    ["0" * 32, "short", "G" * 32, "*", "?" * 32, "0" * 31 + "*"],
    ids=["missing", "too-short", "non-hex", "glob-star", "glob-question", "glob-suffix"],
)
def test_get_image_with_unknown_or_malformed_id_returns_404(client, png_bytes, image_id) -> None:
    # 先上传一张图：通配符类的 id 如果没被拦住，就会错误地命中它
    client.post("/api/uploads", files={"file": ("q.png", png_bytes, "image/png")})

    # 必须编码：裸的 ? 会被当成查询字符串的开头，请求就不会命中这个路由
    resp = client.get(f"/api/images/{quote(image_id, safe='')}")

    assert resp.status_code == 404
    assert resp.json() == {"code": 404, "message": "图片不存在", "data": None}
