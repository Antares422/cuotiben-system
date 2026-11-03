"""T056：迁移 0002——存量数据映射（true→4、false→1）、关联级联与约束保持。"""

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import make_engine
from app.main import create_app
from tests.test_db_version import OLD_SCHEMA, _exec_script


def _build_old_db_with_tags(data_dir) -> None:
    engine = make_engine(data_dir)
    with engine.begin() as conn:
        _exec_script(conn, OLD_SCHEMA)
        conn.execute(sa.text("INSERT INTO subject (id, name) VALUES (1, '数学')"))
        conn.execute(sa.text("INSERT INTO tag (id, name) VALUES (1, '函数'), (2, '易错')"))
        conn.execute(
            sa.text(
                "INSERT INTO mistake (id, content, subject_id, mastered, created_at, updated_at)"
                " VALUES (1, '掌握题', 1, 1, '2026-09-01 08:00:00', '2026-09-01 08:00:00'),"
                " (2, '半掌握题', 1, 1, '2026-09-02 08:00:00', '2026-09-02 08:00:00'),"
                " (3, '未掌握题', 1, 0, '2026-09-03 08:00:00', '2026-09-03 08:00:00')"
            )
        )
        conn.execute(
            sa.text("INSERT INTO mistake_tag (mistake_id, tag_id) VALUES (1, 1), (1, 2), (3, 2)")
        )
    engine.dispose()


def test_migration_maps_every_row(tmp_path, clock) -> None:
    """存量数据逐行映射：mastered=true→4、false→1，mastered_at 一律 NULL。"""
    _build_old_db_with_tags(tmp_path)
    settings = Settings(data_dir=tmp_path, ocr_engine="fake")
    with TestClient(create_app(settings, clock=clock)):
        engine = make_engine(tmp_path)
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text("SELECT id, mastery_level, mastered_at FROM mistake ORDER BY id")
            ).all()
            tags = conn.execute(
                sa.text("SELECT mistake_id, tag_id FROM mistake_tag ORDER BY mistake_id, tag_id")
            ).all()
        engine.dispose()
    assert rows == [(1, 4, None), (2, 4, None), (3, 1, None)]
    # 关联数据原样保留
    assert tags == [(1, 1), (1, 2), (3, 2)]


def test_migration_keeps_cascade_and_unique(tmp_path, clock) -> None:
    """升级后：删除错题仍级联清理关联，subject/tag 的唯一约束仍然有效。"""
    _build_old_db_with_tags(tmp_path)
    settings = Settings(data_dir=tmp_path, ocr_engine="fake")
    with TestClient(create_app(settings, clock=clock)):
        pass
    engine = make_engine(tmp_path)
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM mistake WHERE id = 1"))
    with engine.connect() as conn:
        leftover = conn.execute(
            sa.text("SELECT COUNT(*) FROM mistake_tag WHERE mistake_id = 1")
        ).scalar()
    assert leftover == 0
    with engine.begin() as conn:
        try:
            conn.execute(sa.text("INSERT INTO subject (name) VALUES ('数学')"))
            raise AssertionError("唯一约束失效：重名学科插入成功")
        except sa.exc.IntegrityError:
            pass
    engine.dispose()
