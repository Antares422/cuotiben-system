from fastapi.testclient import TestClient

from app.main import create_app


def test_saved_data_and_image_survive_an_app_restart(settings, clock, png_bytes) -> None:
    with TestClient(create_app(settings, clock=clock)) as first_run:
        subjects = first_run.get("/api/subjects").json()["data"]["items"]
        image_id = first_run.post(
            "/api/uploads", files={"file": ("q.png", png_bytes, "image/png")}
        ).json()["data"]["image_id"]
        saved = first_run.post(
            "/api/mistakes",
            json={
                "content": "重启前保存的题",
                "subject_id": subjects[0]["id"],
                "tags": ["标签"],
                "image_id": image_id,
            },
        ).json()["data"]

    with TestClient(create_app(settings, clock=clock)) as second_run:
        assert second_run.get(f"/api/mistakes/{saved['id']}").json()["data"] == saved
        assert second_run.get(saved["image_url"]).content == png_bytes
        # 默认学科只在第一次启动时写入，重启不能重复
        assert second_run.get("/api/subjects").json()["data"]["items"] == subjects
