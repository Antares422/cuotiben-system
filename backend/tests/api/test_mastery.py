"""T021–T023：PUT /api/mistakes/{id}/mastery 设置掌握程度。"""

import pytest


def _add(client, math_id, content="某道题") -> int:
    resp = client.post("/api/mistakes", json={"content": content, "subject_id": math_id})
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


def _put(client, mistake_id: int, payload) -> dict:
    return client.put(f"/api/mistakes/{mistake_id}/mastery", json=payload)


# T021：设置成功返回完整错题并更新 updated_at；升到四级写入 mastered_at（注入时钟）
def test_set_mastery_returns_full_mistake_and_updates_timestamps(client, clock, math_id) -> None:
    mistake_id = _add(client, math_id)

    clock.advance(minutes=10)
    resp = _put(client, mistake_id, {"level": 3})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    data = body["data"]
    assert data["id"] == mistake_id
    assert data["content"] == "某道题"
    assert data["subject"] == {"id": math_id, "name": "数学"}
    assert data["mastery_level"] == 3
    assert data["mastered_at"] is None
    assert data["created_at"] == "2026-10-03T08:30:00Z"
    assert data["updated_at"] == "2026-10-03T08:40:00Z"


def test_rising_to_level_four_records_mastered_at(client, clock, math_id) -> None:
    mistake_id = _add(client, math_id)

    clock.advance(hours=2)
    resp = _put(client, mistake_id, {"level": 4})

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["mastery_level"] == 4
    assert data["mastered_at"] == "2026-10-03T10:30:00Z"
    assert data["updated_at"] == "2026-10-03T10:30:00Z"


def test_moving_between_mastered_levels_keeps_mastered_at(client, clock, math_id) -> None:
    mistake_id = _add(client, math_id)
    clock.advance(hours=2)
    _put(client, mistake_id, {"level": 4})
    first_mastered_at = _put(client, mistake_id, {"level": 5}).json()["data"]["mastered_at"]

    clock.advance(days=1)
    data = _put(client, mistake_id, {"level": 4}).json()["data"]

    assert data["mastered_at"] == first_mastered_at
    assert data["updated_at"] == "2026-10-04T10:30:00Z"


# T022：降级到三级及以下清空 mastered_at；降级再升回按新时刻重记
def test_downgrading_below_four_clears_mastered_at(client, clock, math_id) -> None:
    mistake_id = _add(client, math_id)
    clock.advance(hours=2)
    _put(client, mistake_id, {"level": 5})

    clock.advance(minutes=30)
    data = _put(client, mistake_id, {"level": 3}).json()["data"]

    assert data["mastery_level"] == 3
    assert data["mastered_at"] is None
    assert data["updated_at"] == "2026-10-03T11:00:00Z"


def test_downgrade_then_rise_again_records_new_mastered_at(client, clock, math_id) -> None:
    mistake_id = _add(client, math_id)
    clock.advance(hours=2)
    _put(client, mistake_id, {"level": 4})

    clock.advance(hours=1)
    _put(client, mistake_id, {"level": 2})
    clock.advance(hours=1)
    data = _put(client, mistake_id, {"level": 4}).json()["data"]

    assert data["mastered_at"] == "2026-10-03T12:30:00Z"


def test_setting_same_level_is_idempotent_and_keeps_mastered_at(client, clock, math_id) -> None:
    mistake_id = _add(client, math_id)
    clock.advance(hours=2)
    _put(client, mistake_id, {"level": 4})

    clock.advance(days=1)
    data = _put(client, mistake_id, {"level": 4}).json()["data"]

    assert data["mastery_level"] == 4
    assert data["mastered_at"] == "2026-10-03T10:30:00Z"
    assert data["updated_at"] == "2026-10-03T10:30:00Z"


# T023：错题不存在 404；level 缺失或非 1~5 整数 422
def test_set_mastery_on_unknown_mistake_returns_404(client) -> None:
    resp = _put(client, 9999, {"level": 3})

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert body["message"] == "错题不存在"
    assert body["data"] is None


def test_set_mastery_without_level_returns_422(client, math_id) -> None:
    mistake_id = _add(client, math_id)

    resp = _put(client, mistake_id, {})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == "掌握程度不能为空"
    assert body["data"] == {"fields": [{"field": "level", "message": "不能为空"}]}


@pytest.mark.parametrize(
    "level", [0, 6, -1, "x", 2.5], ids=["zero", "six", "negative", "text", "float"]
)
def test_set_mastery_with_invalid_level_returns_422(client, math_id, level) -> None:
    mistake_id = _add(client, math_id)

    resp = _put(client, mistake_id, {"level": level})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] in ("掌握程度超出范围", "掌握程度格式不正确")
