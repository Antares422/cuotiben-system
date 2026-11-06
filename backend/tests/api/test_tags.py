"""T011、T036–T039：GET /api/tags 与标签重命名、删除。"""

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db import make_engine


def _add(client, math_id, content, tags=None, **extra) -> int:
    payload = {"content": content, "subject_id": math_id}
    if tags:
        payload["tags"] = tags
    payload.update(extra)
    resp = client.post("/api/mistakes", json=payload)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


def _tag_list(client) -> list[dict]:
    resp = client.get("/api/tags")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    return body["data"]["items"]


def _tag_id(client, name: str) -> int:
    return next(t["id"] for t in _tag_list(client) if t["name"] == name)


# T011：含 0 次使用的标签、按名称排序、带 mistake_count。
# 注：业务路径产生的孤儿标签会被自动清理（T072），0 使用标签只能直接插入得到。
def test_list_tags_includes_unused_tags_sorted_by_name_with_counts(
    client, math_id, settings
) -> None:
    _add(client, math_id, "题一", tags=["函数"])
    _add(client, math_id, "题二", tags=["函数", "几何"])
    engine = make_engine(settings.data_dir)
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tag (name) VALUES ('临时')"))
    engine.dispose()

    items = _tag_list(client)

    # 按名称排序：临(U+4E34) < 几(U+51E0) < 函(U+51FD)
    assert [(t["name"], t["mistake_count"]) for t in items] == [
        ("临时", 0),
        ("几何", 1),
        ("函数", 2),
    ]


def test_list_tags_when_empty_returns_empty_list(client) -> None:
    assert _tag_list(client) == []


# T036：重命名成功，带该标签的错题都显示新名
def test_rename_tag_updates_linked_mistakes(client, math_id) -> None:
    _add(client, math_id, "题一", tags=["函数"])
    _add(client, math_id, "题二", tags=["函数"])
    tag_id = _tag_id(client, "函数")

    resp = client.patch(f"/api/tags/{tag_id}", json={"name": "函数与方程"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    assert body["data"] == {"id": tag_id, "name": "函数与方程", "mistake_count": 2}
    assert [(t["name"], t["mistake_count"]) for t in _tag_list(client)] == [("函数与方程", 2)]

    items = client.get("/api/mistakes").json()["data"]["items"]
    assert all(m["tags"] == ["函数与方程"] for m in items)


# T037：改成当前同名返回 200；重名 409；空名 422；不存在 404
def test_rename_tag_to_current_name_returns_200(client, math_id) -> None:
    _add(client, math_id, "题一", tags=["函数"])
    tag_id = _tag_id(client, "函数")

    resp = client.patch(f"/api/tags/{tag_id}", json={"name": "函数"})

    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "函数"


def test_rename_tag_to_existing_name_returns_409(client, math_id) -> None:
    _add(client, math_id, "题一", tags=["函数"])
    _add(client, math_id, "题二", tags=["几何"])
    tag_id = _tag_id(client, "函数")

    resp = client.patch(f"/api/tags/{tag_id}", json={"name": "几何"})

    assert resp.status_code == 409
    assert resp.json() == {"code": 409, "message": "标签已存在", "data": None}


def test_rename_tag_with_blank_name_returns_422_with_resource_label(client, math_id) -> None:
    _add(client, math_id, "题一", tags=["函数"])
    tag_id = _tag_id(client, "函数")

    resp = client.patch(f"/api/tags/{tag_id}", json={"name": "   "})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == "标签名称不能为空"
    assert body["data"] == {"fields": [{"field": "name", "message": "不能为空"}]}


def test_rename_tag_with_too_long_name_returns_422(client, math_id) -> None:
    _add(client, math_id, "题一", tags=["函数"])
    tag_id = _tag_id(client, "函数")

    resp = client.patch(f"/api/tags/{tag_id}", json={"name": "字" * 51})

    assert resp.status_code == 422
    assert resp.json()["message"] == "标签名称超出范围"


def test_rename_unknown_tag_returns_404(client) -> None:
    resp = client.patch("/api/tags/9999", json={"name": "新名"})

    assert resp.status_code == 404
    assert resp.json()["message"] == "标签不存在"


# T038：删除标签只解除关联，错题全部保留
def test_delete_tag_unlinks_mistakes_and_keeps_them_intact(client, math_id) -> None:
    kept_id = _add(client, math_id, "保留的题", tags=["函数", "几何"], answer="42")
    tag_id = _tag_id(client, "函数")
    before = next(
        m for m in client.get("/api/mistakes").json()["data"]["items"] if m["id"] == kept_id
    )

    resp = client.delete(f"/api/tags/{tag_id}")

    assert resp.status_code == 200
    assert resp.json() == {"code": 200, "message": "ok", "data": None}
    assert _tag_list(client) == [
        {"id": _tag_id(client, "几何"), "name": "几何", "mistake_count": 1}
    ]

    after = next(
        m for m in client.get("/api/mistakes").json()["data"]["items"] if m["id"] == kept_id
    )
    assert after["tags"] == ["几何"]
    assert after["content"] == before["content"]
    assert after["answer"] == before["answer"]
    assert after["mastery_level"] == before["mastery_level"]


def test_delete_unknown_tag_returns_404(client) -> None:
    resp = client.delete("/api/tags/9999")

    assert resp.status_code == 404
    assert resp.json()["message"] == "标签不存在"


# T039：删除中途失败整体回滚（变异检验：去掉事务，本测试必须失败）
def test_delete_tag_rolls_back_when_unlink_fails(client, math_id, monkeypatch) -> None:
    _add(client, math_id, "题一", tags=["函数"])
    tag_id = _tag_id(client, "函数")

    original_delete = Session.delete

    def failing_delete(self, instance):
        raise RuntimeError("模拟删除标签失败")

    monkeypatch.setattr(Session, "delete", failing_delete)

    # TestClient 默认把服务端异常重新抛出；无论以何种方式失败，都必须整体回滚
    with pytest.raises(RuntimeError, match="模拟删除标签失败"):
        client.delete(f"/api/tags/{tag_id}")

    monkeypatch.setattr(Session, "delete", original_delete)
    # 数据完全不变：标签还在，关联还在
    assert [(t["name"], t["mistake_count"]) for t in _tag_list(client)] == [("函数", 1)]
