import pytest


def test_create_mistake_returns_201_with_full_object(client, math_id) -> None:
    resp = client.post(
        "/api/mistakes", json={"content": "已知 f(x)=x²，求 f(2)", "subject_id": math_id}
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == 201
    assert body["message"] == "created"
    data = body["data"]
    assert isinstance(data["id"], int)
    assert data == {
        "id": data["id"],
        "content": "已知 f(x)=x²，求 f(2)",
        "answer": None,
        "error_reason": None,
        "subject": {"id": math_id, "name": "数学"},
        "tags": [],
        "image_id": None,
        "image_url": None,
        "mastered": False,
        "created_at": "2026-10-03T08:30:00Z",
        "updated_at": "2026-10-03T08:30:00Z",
    }


@pytest.mark.parametrize("content", ["", "   ", "\n\t "], ids=["empty", "spaces", "whitespace"])
def test_create_mistake_with_blank_content_returns_422(client, math_id, content) -> None:
    resp = client.post("/api/mistakes", json={"content": content, "subject_id": math_id})

    assert resp.status_code == 422
    assert resp.json() == {
        "code": 422,
        "message": "题目内容不能为空",
        "data": {"fields": [{"field": "content", "message": "不能为空"}]},
    }


def test_create_mistake_without_subject_returns_422(client) -> None:
    resp = client.post("/api/mistakes", json={"content": "某道题"})

    assert resp.status_code == 422
    assert resp.json() == {
        "code": 422,
        "message": "学科不能为空",
        "data": {"fields": [{"field": "subject_id", "message": "不能为空"}]},
    }


def test_create_mistake_with_unknown_subject_returns_422(client) -> None:
    resp = client.post("/api/mistakes", json={"content": "某道题", "subject_id": 9999})

    assert resp.status_code == 422
    assert resp.json() == {
        "code": 422,
        "message": "学科不存在",
        "data": {"fields": [{"field": "subject_id", "message": "不存在"}]},
    }


def test_create_mistake_saves_answer_and_error_reason(client, math_id) -> None:
    resp = client.post(
        "/api/mistakes",
        json={
            "content": "1+1=?",
            "subject_id": math_id,
            "answer": "2",
            "error_reason": "粗心算错",
        },
    )

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["answer"] == "2"
    assert data["error_reason"] == "粗心算错"


def test_create_mistake_normalizes_tags_by_trimming_deduping_and_dropping_blanks(
    client, math_id
) -> None:
    resp = client.post(
        "/api/mistakes",
        json={
            "content": "求单调区间",
            "subject_id": math_id,
            "tags": ["  函数 ", "单调性", "函数", "   "],
        },
    )

    assert resp.status_code == 201
    assert resp.json()["data"]["tags"] == ["函数", "单调性"]


def test_two_mistakes_can_share_the_same_tag(client, math_id) -> None:
    first = client.post(
        "/api/mistakes", json={"content": "题一", "subject_id": math_id, "tags": ["函数"]}
    )
    second = client.post(
        "/api/mistakes", json={"content": "题二", "subject_id": math_id, "tags": ["函数"]}
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["data"]["tags"] == ["函数"]


def test_tags_are_returned_sorted_by_name_regardless_of_input_order(client, math_id) -> None:
    resp = client.post(
        "/api/mistakes", json={"content": "题", "subject_id": math_id, "tags": ["b", "c", "a"]}
    )

    assert resp.json()["data"]["tags"] == ["a", "b", "c"]


def test_create_mistake_links_uploaded_image(client, math_id, png_bytes) -> None:
    image_id = client.post(
        "/api/uploads", files={"file": ("q.png", png_bytes, "image/png")}
    ).json()["data"]["image_id"]

    resp = client.post(
        "/api/mistakes", json={"content": "看图作答", "subject_id": math_id, "image_id": image_id}
    )

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["image_id"] == image_id
    assert data["image_url"] == f"/api/images/{image_id}"
    assert client.get(data["image_url"]).content == png_bytes


@pytest.mark.parametrize(
    "image_id", ["0" * 32, "../../etc/passwd", "*"], ids=["missing", "traversal", "glob"]
)
def test_create_mistake_with_unknown_image_returns_422(client, math_id, image_id) -> None:
    resp = client.post(
        "/api/mistakes", json={"content": "题", "subject_id": math_id, "image_id": image_id}
    )

    assert resp.status_code == 422
    assert resp.json() == {
        "code": 422,
        "message": "图片不存在",
        "data": {"fields": [{"field": "image_id", "message": "不存在"}]},
    }
