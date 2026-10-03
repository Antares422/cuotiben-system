import io
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import create_app


class FakeClock:
    """可手动拨动的时钟，让依赖时间的行为（排序、时间戳）可以精确测试。"""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **delta: float) -> None:
        self._now += timedelta(**delta)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 10, 3, 8, 30, tzinfo=UTC))


@pytest.fixture
def settings(tmp_path) -> Settings:
    # 每个用例独享一个临时数据目录（数据库和图片都在里面），互不影响
    return Settings(data_dir=tmp_path, ocr_engine="fake")


@pytest.fixture
def client(settings: Settings, clock: FakeClock) -> Iterator[TestClient]:
    with TestClient(create_app(settings, clock=clock)) as c:
        yield c


@pytest.fixture
def math_id(client: TestClient) -> int:
    items = client.get("/api/subjects").json()["data"]["items"]
    return next(s["id"] for s in items if s["name"] == "数学")


@pytest.fixture
def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return buffer.getvalue()
