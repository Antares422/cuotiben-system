DEFAULT_SUBJECTS = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]


def test_list_subjects_returns_seeded_defaults(client) -> None:
    resp = client.get("/api/subjects")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    items = body["data"]["items"]
    assert [s["name"] for s in items] == DEFAULT_SUBJECTS
    assert all(isinstance(s["id"], int) for s in items)


def test_create_subject_returns_201_and_appears_in_list(client) -> None:
    resp = client.post("/api/subjects", json={"name": "信息技术"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == 201
    assert body["message"] == "created"
    assert body["data"]["name"] == "信息技术"
    names = [s["name"] for s in client.get("/api/subjects").json()["data"]["items"]]
    assert names[-1] == "信息技术"


def test_create_duplicate_subject_returns_409(client) -> None:
    resp = client.post("/api/subjects", json={"name": "数学"})

    assert resp.status_code == 409
    assert resp.json() == {"code": 409, "message": "学科已存在", "data": None}


def test_create_subject_with_blank_name_returns_422(client) -> None:
    resp = client.post("/api/subjects", json={"name": "   "})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == "学科名称不能为空"
    assert body["data"] == {"fields": [{"field": "name", "message": "不能为空"}]}


def test_create_subject_trims_whitespace_so_padded_duplicate_is_rejected(client) -> None:
    resp = client.post("/api/subjects", json={"name": "  数学  "})

    assert resp.status_code == 409
