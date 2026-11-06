"""T047–T050：数据库版本化——基线登记、自动升级、拒绝更新的库、结构与模型一致。"""

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import Base, make_engine
from app.db_version import LATEST, check_schema_matches_model
from app.main import create_app
from app.models import Mistake

# 迭代 1 的表结构（create_all 生成、无版本记录），用于模拟旧库
OLD_SCHEMA = """
CREATE TABLE subject (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);
CREATE TABLE tag (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);
CREATE TABLE mistake (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    answer TEXT,
    error_reason TEXT,
    subject_id INTEGER NOT NULL REFERENCES subject(id),
    image_id VARCHAR(32),
    mastered BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
CREATE TABLE mistake_tag (
    mistake_id INTEGER NOT NULL REFERENCES mistake(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tag(id),
    PRIMARY KEY (mistake_id, tag_id)
);
"""


def _exec_script(conn, script: str) -> None:
    for stmt in script.split(";"):
        if stmt.strip():
            conn.execute(sa.text(stmt))


def _build_old_db(data_dir) -> None:
    engine = make_engine(data_dir)
    with engine.begin() as conn:
        _exec_script(conn, OLD_SCHEMA)
        conn.execute(sa.text("INSERT INTO subject (id, name) VALUES (1, '数学')"))
        conn.execute(
            sa.text(
                "INSERT INTO mistake (id, content, subject_id, mastered, created_at, updated_at)"
                " VALUES (1, '旧题已掌握', 1, 1, '2026-09-01 08:00:00', '2026-09-01 08:00:00'),"
                " (2, '旧题未掌握', 1, 0, '2026-09-02 08:00:00', '2026-09-02 08:00:00')"
            )
        )
    engine.dispose()


def _db_version(data_dir) -> str:
    engine = make_engine(data_dir)
    with engine.connect() as conn:
        version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
    engine.dispose()
    return version


def test_new_db_is_versioned_as_latest(tmp_path, settings, clock) -> None:
    """T047：新库启动后数据库版本为最新。"""
    with TestClient(create_app(settings, clock=clock)):
        pass
    assert _db_version(tmp_path) == LATEST


def test_old_db_is_registered_and_data_survives(tmp_path, clock) -> None:
    """T048：旧库（无版本记录、带数据）启动后登记基线并升级，数据一条不丢。"""
    _build_old_db(tmp_path)
    settings = Settings(data_dir=tmp_path, ocr_engine="fake")
    with TestClient(create_app(settings, clock=clock)) as client:
        assert _db_version(tmp_path) == LATEST
        # 数据还在，且经迁移 0002 映射（true→4、false→1）
        engine = make_engine(tmp_path)
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text("SELECT content, mastery_level, mastered_at FROM mistake ORDER BY id")
            ).all()
        engine.dispose()
        assert rows == [
            ("旧题已掌握", 4, None),
            ("旧题未掌握", 1, None),
        ]
        # 应用层面正常工作：列表接口返回迁移后的结构
        resp = client.get("/api/mistakes")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert [m["mastery_level"] for m in items] == [1, 4]
        assert all(m["mastered_at"] is None for m in items)


def test_newer_db_is_refused(tmp_path, clock) -> None:
    """T049：库的版本比代码新时拒绝启动，并给出明确原因。"""
    engine = make_engine(tmp_path)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(sa.text("INSERT INTO alembic_version (version_num) VALUES ('9999')"))
    engine.dispose()
    settings = Settings(data_dir=tmp_path, ocr_engine="fake")
    with (
        pytest.raises(RuntimeError, match="9999"),
        TestClient(create_app(settings, clock=clock)),
    ):
        pass


def test_schema_matches_model(tmp_path) -> None:
    """T050（正向）：迁移到最新后的表结构与 ORM 模型一致。"""
    engine = make_engine(tmp_path)
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        check_schema_matches_model(conn)  # 不抛异常即通过


def test_schema_check_fails_when_model_has_extra_column(tmp_path) -> None:
    """T050（变异检验）：模型临时加一列而库没有，检查必须失败。"""
    engine = make_engine(tmp_path)
    Base.metadata.create_all(engine)
    ghost = sa.Column("ghost", sa.String(10))
    Mistake.__table__.append_column(ghost)
    try:
        with engine.connect() as conn, pytest.raises(RuntimeError, match="ghost"):
            check_schema_matches_model(conn)
    finally:
        Mistake.__table__._columns.remove(ghost)
