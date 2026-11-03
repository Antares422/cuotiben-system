"""T001–T010：GET /api/mistakes 组合筛选与搜索。"""

import pytest


def _subject_id(client, name: str) -> int:
    items = client.get("/api/subjects").json()["data"]["items"]
    return next(s["id"] for s in items if s["name"] == name)


def _add(client, subject_id: int, content: str, **extra) -> int:
    payload = {"content": content, "subject_id": subject_id}
    payload.update(extra)
    resp = client.post("/api/mistakes", json=payload)
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


def _set_level(client, mistake_id: int, level: int) -> None:
    resp = client.put(f"/api/mistakes/{mistake_id}/mastery", json={"level": level})
    assert resp.status_code == 200


def _page(client, **params) -> dict:
    resp = client.get("/api/mistakes", params=params)
    assert resp.status_code == 200
    return resp.json()["data"]


def _contents(client, **params) -> list[str]:
    return [i["content"] for i in _page(client, **params)["items"]]


# T001：按 subject_id 筛选，total 为筛选后总数
def test_filter_by_subject_id(client, math_id) -> None:
    physics_id = _add_subject(client, "信息技术")
    _add(client, math_id, "数学题一")
    _add(client, math_id, "数学题二")
    _add(client, physics_id, "信息题一")

    data = _page(client, subject_id=math_id)

    assert [i["content"] for i in data["items"]] == ["数学题二", "数学题一"]
    assert data["total"] == 2


def _add_subject(client, name: str) -> int:
    resp = client.post("/api/subjects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


# T002：按单个标签筛选
def test_filter_by_single_tag(client, math_id) -> None:
    _add(client, math_id, "带函数标签", tags=["函数"])
    _add(client, math_id, "带几何标签", tags=["几何"])
    _add(client, math_id, "无标签")

    assert _contents(client, tag="函数") == ["带函数标签"]


# T003：重复的 tag 参数取交集
def test_filter_by_repeated_tags_takes_intersection(client, math_id) -> None:
    _add(client, math_id, "两者都有", tags=["函数", "几何"])
    _add(client, math_id, "只有函数", tags=["函数"])

    params = [("tag", "函数"), ("tag", "几何")]
    resp = client.get("/api/mistakes", params=params)
    assert resp.status_code == 200
    assert [i["content"] for i in resp.json()["data"]["items"]] == ["两者都有"]
    assert resp.json()["data"]["total"] == 1


# T004：掌握程度区间（含端点）；倒置返回 200 空列表
def test_filter_by_mastery_range_inclusive(client, math_id) -> None:
    low = _add(client, math_id, "一级")
    mid = _add(client, math_id, "三级")
    high = _add(client, math_id, "五级")
    _set_level(client, low, 1)
    _set_level(client, mid, 3)
    _set_level(client, high, 5)

    assert _contents(client, mastery_min=2) == ["五级", "三级"]
    assert _contents(client, mastery_max=3) == ["三级", "一级"]
    assert _contents(client, mastery_min=3, mastery_max=4) == ["三级"]

    data = _page(client, mastery_min=4, mastery_max=2)
    assert data["items"] == []
    assert data["total"] == 0


# T005：关键字同时搜 content、answer、error_reason
def test_filter_by_keyword_matches_multiple_fields(client, math_id) -> None:
    _add(client, math_id, "题目里有苹果", answer="答案没有")
    _add(client, math_id, "题目没有", answer="答案里有苹果")
    _add(client, math_id, "都没有", error_reason="错因提到苹果")
    _add(client, math_id, "完全无关")

    assert sorted(_contents(client, q="苹果")) == sorted(
        [
            "题目没有",
            "题目里有苹果",
            "都没有",
        ]
    )


# T006：不区分英文大小写、忽略首尾空格、全空白等同没有关键字
def test_filter_by_keyword_is_case_insensitive_and_trims(client, math_id) -> None:
    _add(client, math_id, "Calculate the Slope", answer="Two")
    _add(client, math_id, "别的题")

    assert _contents(client, q="calculate") == ["Calculate the Slope"]
    assert _contents(client, q="  CALCULATE  ") == ["Calculate the Slope"]
    assert _contents(client, q="   ") == ["别的题", "Calculate the Slope"]


# T007：% 与 _ 按普通字符匹配（变异检验：去掉转义，本测试必须失败）
@pytest.mark.parametrize(
    ("literal", "other"),
    [("a_b", "axb"), ("50%通过率", "50分及格"), ("100\\元", "100x元")],
    ids=["underscore", "percent", "backslash"],
)
def test_filter_by_keyword_treats_like_wildcards_as_literals(
    client, math_id, literal, other
) -> None:
    _add(client, math_id, literal)
    _add(client, math_id, other)

    assert _contents(client, q=literal) == [literal]


# T008：四类条件组合取交集，保持从新到旧；与内存计算逐条对照
DATASET = [
    {
        "content": "二次函数求最值",
        "subject": "数学",
        "tags": ["函数"],
        "level": 1,
        "answer": "最小值是2",
        "error_reason": "漏掉对称轴",
    },
    {
        "content": "圆的切线",
        "subject": "数学",
        "tags": ["函数", "几何"],
        "level": 3,
        "answer": "x+y=1",
        "error_reason": None,
    },
    {
        "content": "立体几何体积",
        "subject": "数学",
        "tags": ["几何"],
        "level": 5,
        "answer": "V=8",
        "error_reason": "公式记错",
    },
    {
        "content": "Newton second law",
        "subject": "物理",
        "tags": ["力学"],
        "level": 2,
        "answer": "F=ma",
        "error_reason": "单位看错",
    },
    {
        "content": "电磁感应综合",
        "subject": "物理",
        "tags": [],
        "level": 4,
        "answer": None,
        "error_reason": None,
    },
]


def _expected(subject=None, tags=(), mastery_min=None, mastery_max=None, q=None) -> list[str]:
    """在内存里按同一套规则算出期望结果（从新到旧 = 插入顺序倒序）。"""
    if mastery_min is not None and mastery_max is not None and mastery_min > mastery_max:
        return []
    rows = list(DATASET)
    if subject is not None:
        rows = [r for r in rows if r["subject"] == subject]
    for name in tags:
        rows = [r for r in rows if name in r["tags"]]
    if mastery_min is not None:
        rows = [r for r in rows if r["level"] >= mastery_min]
    if mastery_max is not None:
        rows = [r for r in rows if r["level"] <= mastery_max]
    if q:
        needle = q.strip().lower()
        rows = [
            r
            for r in rows
            if any(
                needle in (r[key] or "").lower() for key in ("content", "answer", "error_reason")
            )
        ]
    return [r["content"] for r in reversed(rows)]


@pytest.fixture
def dataset(client, math_id) -> None:
    physics_id = _subject_id(client, "物理")
    subject_ids = {"数学": math_id, "物理": physics_id}
    for row in DATASET:
        mistake_id = _add(
            client,
            subject_ids[row["subject"]],
            row["content"],
            tags=row["tags"],
            answer=row["answer"],
            error_reason=row["error_reason"],
        )
        if row["level"] != 1:
            _set_level(client, mistake_id, row["level"])


@pytest.mark.parametrize(
    ("params", "kwargs"),
    [
        ({"subject_id": "数学"}, {"subject": "数学"}),
        ({"tag": "函数"}, {"tags": ("函数",)}),
        ([("tag", "函数"), ("tag", "几何")], {"tags": ("函数", "几何")}),
        ({"mastery_min": 3}, {"mastery_min": 3}),
        ({"mastery_max": 2}, {"mastery_max": 2}),
        ({"mastery_min": 2, "mastery_max": 4}, {"mastery_min": 2, "mastery_max": 4}),
        ({"q": "单位"}, {"q": "单位"}),
        ({"q": "APPLE"}, {"q": "APPLE"}),  # 无匹配关键字，期望为空
        (
            {"subject_id": "数学", "tag": "几何", "mastery_min": 3, "q": "公式"},
            {"subject": "数学", "tags": ("几何",), "mastery_min": 3, "q": "公式"},
        ),
        (
            {"subject_id": "物理", "mastery_max": 3, "q": "law"},
            {"subject": "物理", "mastery_max": 3, "q": "law"},
        ),
        (
            [("subject_id", "数学"), ("tag", "函数"), ("tag", "几何"), ("mastery_max", "3")],
            {"subject": "数学", "tags": ("函数", "几何"), "mastery_max": 3},
        ),
        (
            {"subject_id": "数学", "mastery_min": 5, "mastery_max": 1},
            {"subject": "数学", "mastery_min": 5, "mastery_max": 1},
        ),
    ],
    ids=[
        "subject",
        "single-tag",
        "tag-intersection",
        "mastery-min",
        "mastery-max",
        "mastery-range",
        "keyword",
        "keyword-no-match",
        "all-four-combined",
        "subject-mastery-keyword",
        "subject-tag-intersection-range",
        "inverted-range-with-subject",
    ],
)
def test_filter_combinations_match_in_memory_expectation(client, dataset, params, kwargs) -> None:
    expected = _expected(**kwargs)

    resp = client.get("/api/mistakes", params=_resolve_subject_params(client, params))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert [i["content"] for i in data["items"]] == expected
    assert data["total"] == len(expected)


def _resolve_subject_params(client, params):
    """把参数里的学科名换成学科 id（parametrize 里用名字可读性更好）。"""
    if isinstance(params, dict):
        params = dict(params)
        if "subject_id" in params:
            params["subject_id"] = _subject_id(client, params["subject_id"])
        return params
    return [
        (key, _subject_id(client, value) if key == "subject_id" else value) for key, value in params
    ]


# T008 补充：筛选 + 分页保持从新到旧
def test_filter_combined_with_pagination_stays_newest_first(client, dataset) -> None:
    data = _page(client, subject_id=_subject_id(client, "数学"), page=1, page_size=2)
    assert [i["content"] for i in data["items"]] == ["立体几何体积", "圆的切线"]
    assert data["total"] == 3


# T009：未知的 subject_id / tag 返回 200 与空列表
def test_filter_by_unknown_subject_or_tag_returns_200_empty_list(client, math_id) -> None:
    _add(client, math_id, "存在的题", tags=["函数"])

    for params in ({"subject_id": 9999}, {"tag": "不存在的标签"}):
        resp = client.get("/api/mistakes", params=params)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["message"] == "ok"
        assert body["data"]["items"] == []
        assert body["data"]["total"] == 0


# T010：非法参数 422，提示为中文
@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"mastery_min": 0}, "最低掌握程度超出范围"),
        ({"mastery_max": 6}, "最高掌握程度超出范围"),
        ({"mastery_min": "abc"}, "最低掌握程度格式不正确"),
        ({"mastery_max": "x"}, "最高掌握程度格式不正确"),
        ({"q": "字" * 101}, "关键字格式不正确"),
    ],
    ids=["min-0", "max-6", "min-not-int", "max-not-int", "q-too-long"],
)
def test_filter_rejects_invalid_params_with_chinese_message(client, params, message) -> None:
    resp = client.get("/api/mistakes", params=params)

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == message
