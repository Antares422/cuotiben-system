"""T057–T059：PATCH /api/mistakes/{id} 编辑错题。"""

import pytest


def _add(client, math_id, content="原题", **extra) -> int:
    payload = {"content": content, "subject_id": math_id}
    payload.update(extra)
    resp = client.post("/api/mistakes", json=payload)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


def _physics_id(client) -> int:
    items = client.get("/api/subjects").json()["data"]["items"]
    return next(s["id"] for s in items if s["name"] == "物理")


# T057：编辑成功，可改内容、答案、错因、学科、标签、原图关联，返回完整错题
def test_edit_mistake_updates_all_fields(client, math_id, png_bytes) -> None:
    image_id = client.post(
        "/api/uploads", files={"file": ("q.png", png_bytes, "image/png")}
    ).json()["data"]["image_id"]
    mistake_id = _add(client, math_id, "旧内容", answer="旧答案", error_reason="旧错因")
    physics_id = _physics_id(client)

    resp = client.patch(
        f"/api/mistakes/{mistake_id}",
        json={
            "content": "新内容",
            "subject_id": physics_id,
            "answer": "新答案",
            "error_reason": "新错因",
            "tags": ["新标签", "函数"],
            "image_id": image_id,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    data = body["data"]
    assert data["id"] == mistake_id
    assert data["content"] == "新内容"
    assert data["answer"] == "新答案"
    assert data["error_reason"] == "新错因"
    assert data["subject"] == {"id": physics_id, "name": "物理"}
    assert data["tags"] == ["函数", "新标签"]
    assert data["image_id"] == image_id
    assert data["image_url"] == f"/api/images/{image_id}"
    assert data["mastery_level"] == 1
    assert data["mastered_at"] is None


def test_edit_mistake_can_replace_image_with_none(client, math_id, png_bytes) -> None:
    image_id = client.post(
        "/api/uploads", files={"file": ("q.png", png_bytes, "image/png")}
    ).json()["data"]["image_id"]
    mistake_id = _add(client, math_id, "带图的题", image_id=image_id)

    resp = client.patch(
        f"/api/mistakes/{mistake_id}",
        json={"content": "带图的题", "subject_id": math_id, "image_id": None},
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["image_id"] is None
    assert resp.json()["data"]["image_url"] is None


# T058：编辑校验与录入一致
@pytest.mark.parametrize("content", ["", "   "])
def test_edit_mistake_with_blank_content_returns_422(client, math_id, content) -> None:
    mistake_id = _add(client, math_id)

    resp = client.patch(
        f"/api/mistakes/{mistake_id}",
        json={"content": content, "subject_id": math_id},
    )

    assert resp.status_code == 422
    assert resp.json() == {
        "code": 422,
        "message": "题目内容不能为空",
        "data": {"fields": [{"field": "content", "message": "不能为空"}]},
    }


def test_edit_mistake_with_unknown_subject_returns_422(client, math_id) -> None:
    mistake_id = _add(client, math_id)

    resp = client.patch(f"/api/mistakes/{mistake_id}", json={"content": "题", "subject_id": 9999})

    assert resp.status_code == 422
    assert resp.json() == {
        "code": 422,
        "message": "学科不存在",
        "data": {"fields": [{"field": "subject_id", "message": "不存在"}]},
    }


def test_edit_mistake_with_unknown_image_returns_422(client, math_id) -> None:
    mistake_id = _add(client, math_id)

    resp = client.patch(
        f"/api/mistakes/{mistake_id}",
        json={"content": "题", "subject_id": math_id, "image_id": "0" * 32},
    )

    assert resp.status_code == 422
    assert resp.json()["message"] == "图片不存在"


def test_edit_unknown_mistake_returns_404(client, math_id) -> None:
    resp = client.patch("/api/mistakes/9999", json={"content": "题", "subject_id": math_id})

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert body["message"] == "错题不存在"
    assert body["data"] is None


# T059：不动 mastery_level / mastered_at / created_at，updated_at 更新（注入时钟断言）
# T072：编辑换标签后，失去全部引用的旧标签被自动删除
def test_edit_removes_orphan_tags(client, math_id) -> None:
    mistake_id = _add(client, math_id, "换标签的题", tags=["旧标签", "共标签"])
    _add(client, math_id, "另一个引用者", tags=["共标签"])

    resp = client.patch(
        f"/api/mistakes/{mistake_id}",
        json={"content": "换标签的题", "subject_id": math_id, "tags": ["新标签"]},
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["tags"] == ["新标签"]
    tags = client.get("/api/tags").json()["data"]["items"]
    assert [(t["name"], t["mistake_count"]) for t in tags] == [("共标签", 1), ("新标签", 1)]


def test_edit_keeps_mastery_and_created_at_but_updates_updated_at(client, clock, math_id) -> None:
    mistake_id = _add(client, math_id)
    clock.advance(hours=1)
    client.put(f"/api/mistakes/{mistake_id}/mastery", json={"level": 4})
    before = client.get(f"/api/mistakes/{mistake_id}").json()["data"]

    clock.advance(days=2)
    resp = client.patch(
        f"/api/mistakes/{mistake_id}",
        json={"content": "改正后的题", "subject_id": math_id},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["content"] == "改正后的题"
    assert data["mastery_level"] == before["mastery_level"] == 4
    assert data["mastered_at"] == before["mastered_at"] == "2026-10-03T09:30:00Z"
    assert data["created_at"] == before["created_at"] == "2026-10-03T08:30:00Z"
    assert data["updated_at"] == "2026-10-05T09:30:00Z"
