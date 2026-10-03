def test_get_mistake_returns_everything_that_was_saved(client, math_id, png_bytes) -> None:
    image_id = client.post(
        "/api/uploads", files={"file": ("q.png", png_bytes, "image/png")}
    ).json()["data"]["image_id"]
    saved = client.post(
        "/api/mistakes",
        json={
            "content": "求 f(x)=x² 在 [0,3] 上的最值",
            "subject_id": math_id,
            "answer": "最大 9，最小 0",
            "error_reason": "忘了检查端点",
            "tags": ["函数", "最值"],
            "image_id": image_id,
        },
    ).json()["data"]

    resp = client.get(f"/api/mistakes/{saved['id']}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    assert body["data"] == saved
    assert body["data"]["subject"] == {"id": math_id, "name": "数学"}
    assert body["data"]["created_at"] == "2026-10-03T08:30:00Z"


def test_get_unknown_mistake_returns_404(client) -> None:
    resp = client.get("/api/mistakes/9999")

    assert resp.status_code == 404
    assert resp.json() == {"code": 404, "message": "错题不存在", "data": None}


def test_get_mistake_with_non_integer_id_returns_422(client) -> None:
    resp = client.get("/api/mistakes/abc")

    assert resp.status_code == 422
    assert resp.json() == {
        "code": 422,
        "message": "错题编号格式不正确",
        "data": {"fields": [{"field": "mistake_id", "message": "格式不正确"}]},
    }
