"""T030–T035、T033：GET /api/subjects 使用数；学科重命名与删除。"""


def _add(client, math_id, content="某道题", **extra) -> int:
    payload = {"content": content, "subject_id": math_id}
    payload.update(extra)
    resp = client.post("/api/mistakes", json=payload)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


def _subject_items(client) -> list[dict]:
    resp = client.get("/api/subjects")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    return body["data"]["items"]


def _subject_id(client, name: str) -> int:
    return next(s["id"] for s in _subject_items(client) if s["name"] == name)


# T030：每项带 mistake_count（含 0）
def test_list_subjects_includes_mistake_count(client, math_id) -> None:
    _add(client, math_id, "数学题一")
    _add(client, math_id, "数学题二")

    items = _subject_items(client)

    assert all(isinstance(s["mistake_count"], int) for s in items)
    math = next(s for s in items if s["name"] == "数学")
    assert math["mistake_count"] == 2
    assert all(s["mistake_count"] == 0 for s in items if s["name"] != "数学")


# T031：重命名成功，所有错题显示新名
def test_rename_subject_updates_mistake_details(client, math_id) -> None:
    mistake_id = _add(client, math_id, "一道数学题")
    subject_id = math_id

    resp = client.patch(f"/api/subjects/{subject_id}", json={"name": "高中数学"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    assert body["data"] == {"id": subject_id, "name": "高中数学", "mistake_count": 1}

    subject = client.get(f"/api/mistakes/{mistake_id}").json()["data"]["subject"]
    assert subject == {"id": subject_id, "name": "高中数学"}


# T032：改成当前同名返回 200；重名 409；空名 422；不存在 404
def test_rename_subject_to_current_name_returns_200(client, math_id) -> None:
    resp = client.patch(f"/api/subjects/{math_id}", json={"name": "数学"})

    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "数学"


def test_rename_subject_to_existing_name_returns_409(client, math_id) -> None:
    resp = client.patch(f"/api/subjects/{math_id}", json={"name": "语文"})

    assert resp.status_code == 409
    assert resp.json() == {"code": 409, "message": "学科已存在", "data": None}


# T033：name 字段提示按资源区分（学科）
def test_rename_subject_with_blank_name_returns_422_with_subject_label(client, math_id) -> None:
    resp = client.patch(f"/api/subjects/{math_id}", json={"name": "   "})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == "学科名称不能为空"
    assert body["data"] == {"fields": [{"field": "name", "message": "不能为空"}]}


def test_rename_subject_with_too_long_name_returns_422(client, math_id) -> None:
    resp = client.patch(f"/api/subjects/{math_id}", json={"name": "字" * 51})

    assert resp.status_code == 422
    assert resp.json()["message"] == "学科名称超出范围"


def test_rename_unknown_subject_returns_404(client) -> None:
    resp = client.patch("/api/subjects/9999", json={"name": "新学科"})

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert body["message"] == "学科不存在"
    assert body["data"] is None


# T034：空学科删除成功，data 为 null
def test_delete_empty_subject_returns_200_with_null_data(client) -> None:
    subject_id = client.post("/api/subjects", json={"name": "信息技术"}).json()["data"]["id"]

    resp = client.delete(f"/api/subjects/{subject_id}")

    assert resp.status_code == 200
    assert resp.json() == {"code": 200, "message": "ok", "data": None}
    assert all(s["name"] != "信息技术" for s in _subject_items(client))


def test_delete_unknown_subject_returns_404(client) -> None:
    resp = client.delete("/api/subjects/9999")

    assert resp.status_code == 404
    assert resp.json()["message"] == "学科不存在"


# T035：学科下有错题时 409，message 含数量，data 带数量，数据不变
def test_delete_subject_with_mistakes_returns_409_and_keeps_everything(client, math_id) -> None:
    _add(client, math_id, "题一")
    _add(client, math_id, "题二")

    resp = client.delete(f"/api/subjects/{math_id}")

    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == 409
    assert body["message"] == "该学科下还有 2 道错题，请先处理这些错题"
    assert body["data"] == {"mistake_count": 2}

    assert _subject_id(client, "数学") == math_id
    assert client.get("/api/mistakes").json()["data"]["total"] == 2
