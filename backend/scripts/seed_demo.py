"""演示数据注入脚本（tasks.md T075）。

用法（在 backend/ 目录下）：

    uv run python scripts/seed_demo.py                  # 写入默认 data/ 目录
    uv run python scripts/seed_demo.py --data-dir 路径   # 指定数据目录

做什么：
- 联网下载若干张题目图片到 ``<data_dir>/images/``（下载失败就本地生成占位图，
  功能演示不受影响）；
- 确保默认学科已存在，并创建一个自创学科（"信息技术"，若不存在）；
- 注入前两个默认学科（按 id 排序）+ 自创学科的演示错题：覆盖各掌握程度、
  掌握时间、标签、答案、错因，总量 >100，用于演示容量提醒与各种筛选；
- 可重复运行：先清除上次注入的演示数据（含演示图片文件）。

注意：只应往本机演示库注入；不要对真实使用的库运行。
"""

import argparse
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw
from sqlalchemy import func, select

from app.db import Base, make_engine, make_session_factory
from app.db_version import ensure_latest
from app.models import Mistake, Subject, Tag, mistake_tag
from app.services.subjects import SubjectService

DEMO_PREFIX = "[演示]"
CUSTOM_SUBJECT_NAME = "信息技术"
SEED = 20261027

# 联网图片来源（picsum 固定种子，保证可复现）；全部失败则退回本地生成
IMAGE_URLS = [f"https://picsum.photos/seed/cuotiben-{i}/640/480" for i in range(1, 7)]

# （计划键, 题量, 题干模板, 答案模板, 错因模板, 标签池）
# 计划键 0/1 = 按 id 排序的前两个默认学科；字符串 = 自创学科名
SUBJECT_PLANS = [
    (
        0,
        40,
        "语文：默写补全第 {n} 题——{kw}，长河落日圆",
        "大漠孤烟直",
        "把「孤烟」写成了「孤燕」，意象记忆混淆",
        ["默写", "古诗词", "易错"],
    ),
    (
        1,
        39,
        "数学：用配方法求 y=x²-{n}x+{n} 的最值（第 {n} 题）",
        "配方得 y=(x-{half})²+{rest}，最小值 {rest}",
        "配方时常数项算错，忘了减半",
        ["函数", "配方", "计算", "易错"],
    ),
    (
        CUSTOM_SUBJECT_NAME,
        31,
        "信息技术：解释第 {n} 题——{kw} 的工作原理",
        "{kw} 通过分组交换把数据逐跳转发到目的地",
        "把{kw}与电路交换的时序特点记混了",
        ["网络", "协议", "概念"],
    ),
]

KEYWORDS = {
    0: ["王维", "边塞", "颈联"],
    CUSTOM_SUBJECT_NAME: ["路由器", "TCP", "分组交换"],
}
SHARED_EXTRA_TAGS = ["常考"]


def _download_image(url: str) -> bytes | None:
    try:
        with urlopen(url, timeout=10) as resp:  # 固定地址，仅演示用途
            content = resp.read()
        # 校验真是图片，并统一转成 JPEG
        with Image.open(BytesIO(content)) as im:
            im = im.convert("RGB")
            out = BytesIO()
            im.save(out, format="JPEG")
        return out.getvalue()
    except OSError:  # 网络/图片错误都退回占位图
        return None


def _placeholder_image(label: str) -> bytes:
    """下载失败时的占位图：纸面底 + 红笔标题。"""
    im = Image.new("RGB", (640, 480), "#fffdf6")
    draw = ImageDraw.Draw(im)
    for y in range(40, 480, 36):
        draw.line([(20, y), (620, y)], fill="#cfe0ee", width=1)
    draw.text((40, 60), label, fill="#d0312d")
    draw.text((40, 110), "(offline placeholder)", fill="#1f2a44")
    out = BytesIO()
    im.save(out, format="JPEG")
    return out.getvalue()


def _prepare_images(images_dir: Path) -> list[str]:
    images_dir.mkdir(parents=True, exist_ok=True)
    image_ids: list[str] = []
    for i, url in enumerate(IMAGE_URLS):
        content = _download_image(url)
        if content is None:
            content = _placeholder_image(f"Demo question {i + 1}")
        image_id = uuid.uuid4().hex
        (images_dir / f"{image_id}.jpg").write_bytes(content)
        image_ids.append(image_id)
    return image_ids


def _clear_old_demo(session) -> list[str]:
    """清除旧的演示错题与其引用，返回可删除的图片 id。"""
    old = session.scalars(select(Mistake).where(Mistake.content.like(f"{DEMO_PREFIX}%"))).all()
    image_ids = [m.image_id for m in old if m.image_id]
    for m in old:
        session.delete(m)
    # 可达性清理：无引用标签一并删除
    orphan_ids = session.scalars(
        select(Tag.id).where(~Tag.id.in_(select(mistake_tag.c.tag_id)))
    ).all()
    for tag_id in orphan_ids:
        tag = session.get(Tag, tag_id)
        if tag is not None:
            session.delete(tag)
    session.commit()
    return image_ids


def _resolve_subject_ids(session) -> dict[int | str, int]:
    """把计划键解析成 subject_id：0/1 = 按 id 排序的前两个默认学科。"""
    defaults = session.scalars(select(Subject).order_by(Subject.id)).all()[:2]
    ids: dict[int | str, int] = {i: s.id for i, s in enumerate(defaults)}
    custom = session.scalar(select(Subject).where(Subject.name == CUSTOM_SUBJECT_NAME))
    if custom is None:
        custom = Subject(name=CUSTOM_SUBJECT_NAME)
        session.add(custom)
        session.flush()
    ids[CUSTOM_SUBJECT_NAME] = custom.id
    return ids


def _make_mistakes(session, subject_ids, image_ids) -> int:
    rng = random.Random(SEED)
    now = datetime.now(UTC)
    count = 0
    for key, amount, content_tpl, answer_tpl, reason_tpl, tag_pool in SUBJECT_PLANS:
        subject_id = subject_ids[key]
        for n in range(1, amount + 1):
            kw = rng.choice(KEYWORDS.get(key, ["考点"]))
            half = n / 2
            content = DEMO_PREFIX + content_tpl.format(n=n, kw=kw, half=half, rest=n - half * half)
            answer = answer_tpl.format(n=n, kw=kw, half=half, rest=n - half * half)
            reason = reason_tpl.format(kw=kw)
            # 掌握程度分布：一级 35% / 二级 25% / 三级 15% / 四级 15% / 五级 10%
            roll = rng.random()
            level = (
                1
                if roll < 0.35
                else 2
                if roll < 0.60
                else 3
                if roll < 0.75
                else 4
                if roll < 0.90
                else 5
            )
            created = now - timedelta(days=rng.randint(0, 30), hours=rng.randint(0, 23))
            mastered_at = created + timedelta(days=rng.randint(1, 5)) if level >= 4 else None
            tags = rng.sample(tag_pool, k=rng.randint(1, min(2, len(tag_pool))))
            if rng.random() < 0.3:
                tags.append(rng.choice(SHARED_EXTRA_TAGS))
            mistake = Mistake(
                content=content,
                answer=answer,
                error_reason=reason,
                subject_id=subject_id,
                image_id=rng.choice(image_ids) if rng.random() < 0.6 else None,
                mastery_level=level,
                mastered_at=mastered_at,
                created_at=created,
                updated_at=created,
            )
            mistake.tags = [
                session.scalar(select(Tag).where(Tag.name == name)) or Tag(name=name)
                for name in dict.fromkeys(tags)
            ]
            session.add(mistake)
            count += 1
    session.commit()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="注入演示数据（可重复运行）")
    parser.add_argument("--data-dir", default="data", help="数据目录（默认 backend/data）")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    engine = make_engine(data_dir)
    Base.metadata.create_all(engine)
    ensure_latest(engine)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        SubjectService(session).seed_defaults()
        stale_images = _clear_old_demo(session)
        image_ids = _prepare_images(data_dir / "images")
        subject_ids = _resolve_subject_ids(session)
        count = _make_mistakes(session, subject_ids, image_ids)

    for image_id in stale_images:
        for stale in (data_dir / "images").glob(f"{image_id}.*"):
            stale.unlink()

    with session_factory() as session:
        total = session.scalar(select(func.count()).select_from(Mistake)) or 0
        by_level = dict(
            session.execute(
                select(Mistake.mastery_level, func.count()).group_by(Mistake.mastery_level)
            ).all()
        )
        tags = session.scalar(select(func.count()).select_from(Tag)) or 0

    print(f"已注入 {count} 道演示错题，库内总题数 {total}（容量提醒阈值 100）")
    print(f"掌握程度分布：{dict(sorted(by_level.items()))}")
    print(f"标签数：{tags}；图片：{len(image_ids)} 张")
    print(
        "启动查看：STATIC_DIR=../frontend/dist uv run uvicorn app.main:create_app --factory --port 8000"
    )


if __name__ == "__main__":
    main()
