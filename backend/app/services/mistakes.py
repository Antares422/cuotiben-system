from collections.abc import Callable
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationFailed
from app.models import Mistake, Subject, Tag, mistake_tag
from app.services.images import ImageService

Clock = Callable[[], datetime]


def _escape_like(text: str) -> str:
    """把 LIKE 通配符当普通字符：先转义反斜杠，再转义 % 和 _。"""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class MistakeService:
    def __init__(self, session: Session, clock: Clock, images: ImageService) -> None:
        self._session = session
        self._clock = clock
        self._images = images

    def create(
        self,
        *,
        content: str,
        subject_id: int,
        answer: str | None = None,
        error_reason: str | None = None,
        tags: list[str] | None = None,
        image_id: str | None = None,
    ) -> Mistake:
        if self._session.get(Subject, subject_id) is None:
            raise ValidationFailed.for_field("subject_id", "不存在", "学科")
        if image_id is not None and not self._images.exists(image_id):
            raise ValidationFailed.for_field("image_id", "不存在", "图片")
        now = self._clock()
        mistake = Mistake(
            content=content,
            subject_id=subject_id,
            answer=answer,
            error_reason=error_reason,
            tags=self._resolve_tags(tags or []),
            image_id=image_id,
            mastery_level=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(mistake)
        self._session.commit()
        return mistake

    def update(
        self,
        mistake_id: int,
        *,
        content: str,
        subject_id: int,
        answer: str | None = None,
        error_reason: str | None = None,
        tags: list[str] | None = None,
        image_id: str | None = None,
    ) -> Mistake:
        """编辑错题：校验规则与录入一致；不改掌握程度与时间戳（除 updated_at）。"""
        mistake = self.get(mistake_id)
        if self._session.get(Subject, subject_id) is None:
            raise ValidationFailed.for_field("subject_id", "不存在", "学科")
        if image_id is not None and not self._images.exists(image_id):
            raise ValidationFailed.for_field("image_id", "不存在", "图片")
        mistake.content = content
        mistake.subject_id = subject_id
        mistake.answer = answer
        mistake.error_reason = error_reason
        mistake.tags = self._resolve_tags(tags or [])
        mistake.image_id = image_id
        mistake.updated_at = self._clock()
        self._delete_orphan_tags()
        self._session.commit()
        return mistake

    def delete(self, mistake_id: int) -> None:
        mistake = self.get(mistake_id)
        if mistake.mastery_level < 4:
            level = mistake.mastery_level
            raise ConflictError(
                f"掌握程度达到四级后才能清理（当前：{level} 级）",
                {"mastery_level": level},
            )
        # mistake_tag 的 mistake_id 外键带 ON DELETE CASCADE，关联行自动清理；
        # 随后做可达性分析：失去全部引用的标签一并删除（research D16）
        self._session.delete(mistake)
        self._delete_orphan_tags()
        self._session.commit()

    def set_mastery(self, mistake_id: int, level: int) -> Mistake:
        mistake = self.get(mistake_id)
        old_level = mistake.mastery_level
        if level != old_level:
            mistake.mastery_level = level
            if old_level < 4 <= level:
                mistake.mastered_at = self._clock()
            elif level < 4:
                mistake.mastered_at = None
            mistake.updated_at = self._clock()
            self._session.commit()
        return mistake

    def get(self, mistake_id: int) -> Mistake:
        mistake = self._session.get(Mistake, mistake_id)
        if mistake is None:
            raise NotFoundError("错题不存在")
        return mistake

    def list_page(
        self,
        *,
        page: int,
        page_size: int,
        subject_id: int | None = None,
        tags: list[str] | None = None,
        mastery_min: int | None = None,
        mastery_max: int | None = None,
        q: str | None = None,
    ) -> tuple[list[Mistake], int, int]:
        """筛选 + 分页，返回 (当前页, 筛选后总数, 不受筛选影响的总数)。

        各条件取交集；`mastery_min > mastery_max` 时自然得到空结果。
        """
        stmt = select(Mistake)
        if subject_id is not None:
            stmt = stmt.where(Mistake.subject_id == subject_id)
        for name in tags or []:
            stmt = stmt.where(Mistake.tags.any(Tag.name == name))
        if mastery_min is not None:
            stmt = stmt.where(Mistake.mastery_level >= mastery_min)
        if mastery_max is not None:
            stmt = stmt.where(Mistake.mastery_level <= mastery_max)
        keyword = (q or "").strip()
        if keyword:
            pattern = f"%{_escape_like(keyword)}%"
            stmt = stmt.where(
                or_(
                    Mistake.content.ilike(pattern, escape="\\"),
                    Mistake.answer.ilike(pattern, escape="\\"),
                    Mistake.error_reason.ilike(pattern, escape="\\"),
                )
            )
        overall_total = self._session.scalar(select(func.count()).select_from(Mistake)) or 0
        total = (
            self._session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
            or 0
        )
        items = self._session.scalars(
            stmt.order_by(Mistake.created_at.desc(), Mistake.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items), total, overall_total

    def _resolve_tags(self, names: list[str]) -> list[Tag]:
        """去掉首尾空白、去重、忽略空白项；已存在的标签复用，不存在的新建。"""
        cleaned = list(dict.fromkeys(n.strip() for n in names if n.strip()))
        return [self._get_or_create_tag(name) for name in cleaned]

    def _get_or_create_tag(self, name: str) -> Tag:
        tag = self._session.scalar(select(Tag).where(Tag.name == name))
        return tag or Tag(name=name)

    def _delete_orphan_tags(self) -> None:
        """可达性清理：删除不再被任何错题引用的标签（research D16）。

        在删除错题或编辑换标签后调用，必须在 commit 之前（同事务）。
        """
        orphan_ids = self._session.scalars(
            select(Tag.id).where(~Tag.id.in_(select(mistake_tag.c.tag_id)))
        ).all()
        for tag_id in orphan_ids:
            tag = self._session.get(Tag, tag_id)
            if tag is not None:
                self._session.delete(tag)
