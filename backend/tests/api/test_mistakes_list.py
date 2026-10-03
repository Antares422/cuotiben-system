import pytest


def test_list_mistakes_when_empty_returns_empty_page(client) -> None:
    resp = client.get("/api/mistakes")

    assert resp.status_code == 200
    assert resp.json() == {
        "code": 200,
        "message": "ok",
        "data": {"items": [], "total": 0, "page": 1, "page_size": 20},
    }


def _add(client, subject_id: int, content: str) -> None:
    resp = client.post("/api/mistakes", json={"content": content, "subject_id": subject_id})
    assert resp.status_code == 201


def _contents(client, **params) -> list[str]:
    items = client.get("/api/mistakes", params=params).json()["data"]["items"]
    return [i["content"] for i in items]


def test_list_orders_newest_first_with_id_as_tiebreaker(client, clock, math_id) -> None:
    _add(client, math_id, "最早")
    clock.advance(minutes=5)
    _add(client, math_id, "同刻甲")
    _add(client, math_id, "同刻乙")
    clock.advance(minutes=5)
    _add(client, math_id, "最新")

    assert _contents(client) == ["最新", "同刻乙", "同刻甲", "最早"]


def test_list_returns_timestamps_in_utc_with_z_suffix(client, math_id) -> None:
    _add(client, math_id, "题")

    item = client.get("/api/mistakes").json()["data"]["items"][0]

    assert item["created_at"] == "2026-10-03T08:30:00Z"
    assert item["updated_at"] == "2026-10-03T08:30:00Z"


def test_list_paginates_and_reports_total(client, clock, math_id) -> None:
    for n in range(1, 6):
        _add(client, math_id, f"第{n}题")
        clock.advance(minutes=1)

    page2 = client.get("/api/mistakes", params={"page": 2, "page_size": 2}).json()["data"]

    assert [i["content"] for i in page2["items"]] == ["第3题", "第2题"]
    assert (page2["total"], page2["page"], page2["page_size"]) == (5, 2, 2)
    assert _contents(client, page=3, page_size=2) == ["第1题"]


def test_list_page_beyond_the_end_returns_empty_items_not_an_error(client, math_id) -> None:
    _add(client, math_id, "唯一一题")

    resp = client.get("/api/mistakes", params={"page": 9, "page_size": 20})

    assert resp.status_code == 200
    assert resp.json()["data"]["items"] == []
    assert resp.json()["data"]["total"] == 1


@pytest.mark.parametrize(
    ("params", "field", "message"),
    [
        ({"page": 0}, "page", "页码超出范围"),
        ({"page": -1}, "page", "页码超出范围"),
        ({"page": "abc"}, "page", "页码格式不正确"),
        ({"page_size": 0}, "page_size", "每页数量超出范围"),
        ({"page_size": 101}, "page_size", "每页数量超出范围"),
    ],
    ids=["page-0", "page-negative", "page-not-int", "size-0", "size-over-max"],
)
def test_list_rejects_invalid_pagination_params_with_422(client, params, field, message) -> None:
    resp = client.get("/api/mistakes", params=params)

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == message
    assert body["data"]["fields"][0]["field"] == field
