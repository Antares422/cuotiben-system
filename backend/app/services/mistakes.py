from collections.abc import Callable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import NotFoundError, ValidationFailed
from app.models import Mistake, Subject, Tag
from app.services.images import ImageService

Clock = Callable[[], datetime]


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
            mastered=False,
            created_at=now,
            updated_at=now,
        )
        self._session.add(mistake)
        self._session.commit()
        return mistake

    def get(self, mistake_id: int) -> Mistake:
        mistake = self._session.get(Mistake, mistake_id)
        if mistake is None:
            raise NotFoundError("错题不存在")
        return mistake

    def list_page(self, *, page: int, page_size: int) -> tuple[list[Mistake], int]:
        total = self._session.scalar(select(func.count()).select_from(Mistake)) or 0
        items = self._session.scalars(
            select(Mistake)
            .order_by(Mistake.created_at.desc(), Mistake.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items), total

    def _resolve_tags(self, names: list[str]) -> list[Tag]:
        """去掉首尾空白、去重、忽略空白项；已存在的标签复用，不存在的新建。"""
        cleaned = list(dict.fromkeys(n.strip() for n in names if n.strip()))
        return [self._get_or_create_tag(name) for name in cleaned]

    def _get_or_create_tag(self, name: str) -> Tag:
        tag = self._session.scalar(select(Tag).where(Tag.name == name))
        return tag or Tag(name=name)
