import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def dist(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>错题本前端</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('app')", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("TOP-SECRET", encoding="utf-8")
    return dist


@pytest.fixture
def web(settings, clock, dist):
    configured = settings.model_copy(update={"static_dir": dist})
    with TestClient(create_app(configured, clock=clock)) as client:
        yield client


def test_root_serves_the_built_frontend_and_its_assets(web) -> None:
    index = web.get("/")
    asset = web.get("/assets/app.js")

    assert index.status_code == 200
    assert "错题本前端" in index.text
    assert asset.status_code == 200
    assert asset.text == "console.log('app')"


@pytest.mark.parametrize("path", ["/mistakes", "/mistakes/5"])
def test_client_side_routes_fall_back_to_the_frontend_on_refresh(web, path) -> None:
    resp = web.get(path)

    assert resp.status_code == 200
    assert "错题本前端" in resp.text


def test_unknown_api_paths_still_return_the_json_envelope_not_the_frontend(web) -> None:
    resp = web.get("/api/does-not-exist")

    assert resp.status_code == 404
    assert resp.json() == {"code": 404, "message": "资源不存在", "data": None}


def test_without_a_static_dir_the_root_is_just_a_json_404(client) -> None:
    resp = client.get("/")

    assert resp.status_code == 404
    assert resp.json()["code"] == 404


@pytest.mark.parametrize(
    "path", ["/..%2Fsecret.txt", "/%2e%2e/secret.txt", "/assets/..%2F..%2Fsecret.txt"]
)
def test_path_traversal_cannot_read_files_outside_the_static_dir(web, path) -> None:
    resp = web.get(path)

    assert "TOP-SECRET" not in resp.text


def test_unknown_api_path_with_a_non_get_method_is_a_json_404(web) -> None:
    resp = web.post("/api/does-not-exist", json={})

    assert resp.status_code == 404
    assert resp.json() == {"code": 404, "message": "资源不存在", "data": None}
