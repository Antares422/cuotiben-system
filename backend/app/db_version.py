"""数据库版本化：Alembic 迁移链的薄封装（宪法 v1.1.0）。

版本链：
- `0001` = 迭代 1 的表结构（基线；旧库无版本记录时自动登记，不改数据）
- `0002` = `mistake.mastered`(BOOL) → `mastery_level`(INTEGER) + 新增 `mastered_at`（见 research D11）

启动时（`ensure_latest`）：
- 库没有版本记录 → 按结构判断：有 `mastered` 列的是旧库，登记 `0001` 后自动升级；
  已是新结构的库直接登记为最新；无法识别则报错。
- 库版本低于代码 → 沿链自动升级。
- 库版本高于代码 → 拒绝启动并说明原因。
- 升级后校验表结构与 ORM 模型一致（改了模型忘写迁移会在这里失败）。

注意：迁移 0002 会重建 `mistake` 表，SQLite 在外键开启时 DROP TABLE 会隐式
DELETE 并级联清空关联表，因此迁移期间必须临时关闭外键（见 _upgrade_0002）。
"""

from collections.abc import Callable
from typing import Any

import sqlalchemy as sa
from alembic.migration import MigrationContext
from sqlalchemy import Connection, Engine

from app.db import Base

BASELINE = "0001"
LATEST = "0002"

Execute = Callable[[str], None]


def _upgrade_0002(execute: Execute) -> None:
    """0001 → 0002：mastered BOOL 改为 mastery_level INTEGER，新增 mastered_at。

    用"建新表 → 复制映射 → 删旧表 → 改名"重建（SQLite 不支持改列类型），
    保留全部存量数据；存量 true(1)→4、false(0)→1（见 data-model.md 的映射表）。
    """
    execute(
        """
        CREATE TABLE mistake_migrated (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            answer TEXT,
            error_reason TEXT,
            subject_id INTEGER NOT NULL REFERENCES subject(id),
            image_id VARCHAR(32),
            mastery_level INTEGER NOT NULL DEFAULT 1,
            mastered_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    execute(
        """
        INSERT INTO mistake_migrated
            (id, content, answer, error_reason, subject_id, image_id,
             mastery_level, mastered_at, created_at, updated_at)
        SELECT id, content, answer, error_reason, subject_id, image_id,
               CASE WHEN mastered = 1 THEN 4 ELSE 1 END, NULL, created_at, updated_at
        FROM mistake
        """
    )
    execute("DROP TABLE mistake")
    execute("ALTER TABLE mistake_migrated RENAME TO mistake")


# 键 = 目标版本号，值 = 从上一版本升级的函数
MIGRATIONS: dict[str, Callable[[Execute], None]] = {"0002": _upgrade_0002}
NEXT: dict[str, str] = {"0001": "0002"}


def _stamp(conn: Connection, version: str) -> None:
    if conn.execute(sa.text("SELECT version_num FROM alembic_version")).first():
        conn.execute(sa.text("UPDATE alembic_version SET version_num = :v"), {"v": version})
    else:
        conn.execute(
            sa.text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": version}
        )


def _has_column(conn: Connection, table: str, column: str) -> bool:
    inspector = sa.inspect(conn)
    return inspector.has_table(table) and column in {
        c["name"] for c in inspector.get_columns(table)
    }


def check_schema_matches_model(conn: Connection) -> None:
    """迁移到最新后的表结构与 ORM 模型一致性校验（T050）。"""
    inspector = sa.inspect(conn)
    problems: list[str] = []
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            problems.append(f"缺少表 {table.name}")
            continue
        actual = {c["name"] for c in inspector.get_columns(table.name)}
        expected = {c.name for c in table.columns}
        if missing := expected - actual:
            problems.append(f"表 {table.name} 缺少列 {sorted(missing)}")
        if extra := actual - expected:
            problems.append(f"表 {table.name} 多出列 {sorted(extra)}")
    if problems:
        raise RuntimeError("数据库结构与模型不一致（可能改了模型忘写迁移）: " + "; ".join(problems))


def ensure_latest(engine: Engine) -> None:
    """把数据库升级到代码所需的最新版本；版本不可识别或更新则拒绝启动。"""
    options: dict[str, Any] = {"isolation_level": "AUTOCOMMIT"}  # PRAGMA 必须在事务外执行
    with engine.connect().execution_options(**options) as conn:
        context = MigrationContext.configure(conn)
        context._ensure_version_table()  # 确保 alembic_version 表存在
        current = context.get_current_revision()
        if current is None:
            if _has_column(conn, "mistake", "mastered"):
                _stamp(conn, BASELINE)  # 旧库（迭代 1 结构）登记基线
                current = BASELINE
            elif _has_column(conn, "mistake", "mastery_level"):
                _stamp(conn, LATEST)  # 新库：结构与代码一致，直接登记为最新
                return
            else:
                raise RuntimeError("数据库缺少 mistake 表，无法确定版本基线")
        known = {BASELINE, *MIGRATIONS.keys()}
        if current not in known:
            raise RuntimeError(f"无法识别的数据库版本 {current}，数据文件可能来自其他版本")
        if current > LATEST:
            raise RuntimeError(
                f"数据库版本 {current} 比代码支持的最新版本 {LATEST} 新，请升级应用后再打开"
            )
        if current != LATEST:
            # DROP TABLE 重建 mistake 期间必须关闭外键，否则级联会清空 mistake_tag
            conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
            try:
                while current != LATEST:
                    target = NEXT[current]
                    MIGRATIONS[target](lambda sql: conn.execute(sa.text(sql)))
                    _stamp(conn, target)
                    current = target
            finally:
                conn.execute(sa.text("PRAGMA foreign_keys=ON"))
        check_schema_matches_model(conn)
