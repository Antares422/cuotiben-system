"""T060–T061、T067：DELETE /api/mistakes/{id} 与列表 overall_total。"""


def _add(client, math_id, content, **extra) -> int:
    payload = {"content": content, "subject_id": math_id}
    payload.update(extra)
    resp = client.post("/api/mistakes", json=payload)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


def _set_level(client, mistake_id: int, level: int) -> None:
    resp = client.put(f"/api/mistakes/{mistake_id}/mastery", json={"level": level})
    assert resp.status_code == 200


# T061：低于四级返回 409，message 含当前等级，data 带等级，题目保持不变
def test_delete_mistake_below_level_four_returns_409_and_keeps_it(client, math_id) -> None:
    mistake_id = _add(client, math_id, "还不够熟练")
    _set_level(client, mistake_id, 3)

    resp = client.delete(f"/api/mistakes/{mistake_id}")

    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == 409
    assert body["message"] == "掌握程度达到四级后才能清理（当前：3 级）"
    assert body["data"] == {"mastery_level": 3}

    detail = client.get(f"/api/mistakes/{mistake_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["content"] == "还不够熟练"


def test_delete_mistake_at_level_one_returns_409(client, math_id) -> None:
    mistake_id = _add(client, math_id, "刚录入的题")

    resp = client.delete(f"/api/mistakes/{mistake_id}")

    assert resp.status_code == 409
    assert resp.json()["message"] == "掌握程度达到四级后才能清理（当前：1 级）"
    assert resp.json()["data"] == {"mastery_level": 1}


def test_delete_unknown_mistake_returns_404(client) -> None:
    resp = client.delete("/api/mistakes/9999")

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert body["message"] == "错题不存在"
    assert body["data"] is None


# T060：四级及以上删除成功 data 为 null，mistake_tag 关联级联清理，其他题与标签不受影响
def test_delete_mastered_mistake_cascades_links_and_keeps_the_rest(client, math_id) -> None:
    doomed_id = _add(client, math_id, "已熟练的题", tags=["函数", "几何"])
    kept_id = _add(client, math_id, "还要复习的题", tags=["函数"])
    _set_level(client, doomed_id, 4)

    resp = client.delete(f"/api/mistakes/{doomed_id}")

    assert resp.status_code == 200
    assert resp.json() == {"code": 200, "message": "ok", "data": None}

    assert client.get(f"/api/mistakes/{doomed_id}").status_code == 404
    assert client.get(f"/api/mistakes/{kept_id}").status_code == 200

    # T072：无人引用的标签"几何"被自动删除；仍被使用的"函数"保留
    tags = client.get("/api/tags").json()["data"]["items"]
    assert [(t["name"], t["mistake_count"]) for t in tags] == [("函数", 1)]


# T072：删除后做可达性分析，失去全部引用的标签一并删除
def test_delete_removes_orphan_tags(client, math_id) -> None:
    doomed_id = _add(client, math_id, "唯一引用者", tags=["孤标签", "共标签"])
    other_id = _add(client, math_id, "另一个引用者", tags=["共标签"])
    _set_level(client, doomed_id, 4)

    resp = client.delete(f"/api/mistakes/{doomed_id}")

    assert resp.status_code == 200
    tags = client.get("/api/tags").json()["data"]["items"]
    assert [(t["name"], t["mistake_count"]) for t in tags] == [("共标签", 1)]
    assert client.get(f"/api/mistakes/{other_id}").status_code == 200


def test_delete_mistake_at_level_five_succeeds(client, math_id) -> None:
    mistake_id = _add(client, math_id, "完全掌握")
    _set_level(client, mistake_id, 5)

    resp = client.delete(f"/api/mistakes/{mistake_id}")

    assert resp.status_code == 200
    assert resp.json()["data"] is None


# T067：overall_total 不受筛选影响
def test_list_overall_total_ignores_filters(client, math_id) -> None:
    physics_id = next(
        s["id"] for s in client.get("/api/subjects").json()["data"]["items"] if s["name"] == "物理"
    )
    _add(client, math_id, "数学题", tags=["函数"])
    _add(client, physics_id, "物理题")

    resp = client.get("/api/mistakes", params={"subject_id": physics_id})

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["overall_total"] == 2


def test_list_overall_total_when_empty(client) -> None:
    data = client.get("/api/mistakes").json()["data"]

    assert data["total"] == 0
    assert data["overall_total"] == 0


# T072：被拒绝的删除（409）不做标签清理
def test_rejected_delete_keeps_orphanable_tags(client, math_id) -> None:
    mistake_id = _add(client, math_id, "还不够熟练", tags=["暂留标签"])

    resp = client.delete(f"/api/mistakes/{mistake_id}")

    assert resp.status_code == 409
    tags = client.get("/api/tags").json()["data"]["items"]
    assert [(t["name"], t["mistake_count"]) for t in tags] == [("暂留标签", 1)]
