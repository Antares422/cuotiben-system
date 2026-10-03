import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.main import create_app


def test_unknown_route_returns_envelope_404(client) -> None:
    resp = client.get("/api/does-not-exist")

    assert resp.status_code == 404
    assert resp.json() == {"code": 404, "message": "资源不存在", "data": None}


def test_wrong_method_returns_envelope_405(settings) -> None:
    app = create_app(settings)

    @app.get("/api/ping")
    def ping() -> dict:
        return {}

    with TestClient(app) as client:
        resp = client.post("/api/ping")

    assert resp.status_code == 405
    assert resp.json() == {"code": 405, "message": "请求方法不允许", "data": None}


def test_unhandled_exception_returns_generic_500_without_leaking_details(settings) -> None:
    app = create_app(settings)

    @app.get("/api/boom")
    def boom() -> dict:
        raise RuntimeError("secret: /etc/passwd")

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/boom")

    assert resp.status_code == 500
    assert resp.json() == {"code": 500, "message": "服务器开小差了，请稍后再试", "data": None}
    assert "secret" not in resp.text


@pytest.mark.parametrize("body", [{}, {"content": ""}], ids=["missing", "empty"])
def test_validation_failure_returns_422_with_field_details(settings, body) -> None:
    app = create_app(settings)

    class Payload(BaseModel):
        content: str = Field(min_length=1)

    @app.post("/api/echo")
    def echo(payload: Payload) -> dict:
        return {}

    with TestClient(app) as client:
        resp = client.post("/api/echo", json=body)

    assert resp.status_code == 422
    assert resp.json() == {
        "code": 422,
        "message": "题目内容不能为空",
        "data": {"fields": [{"field": "content", "message": "不能为空"}]},
    }


def test_malformed_json_returns_400_not_422(settings) -> None:
    app = create_app(settings)

    class Payload(BaseModel):
        content: str

    @app.post("/api/echo")
    def echo(payload: Payload) -> dict:
        return {}

    with TestClient(app) as client:
        resp = client.post(
            "/api/echo", content="{not json", headers={"Content-Type": "application/json"}
        )

    assert resp.status_code == 400
    assert resp.json() == {"code": 400, "message": "请求格式不正确", "data": None}
