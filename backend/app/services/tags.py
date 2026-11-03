from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationFailed
from app.models import Tag, mistake_tag

_NAME_LABEL = "标签名称"
_NAME_MAX_LENGTH = 50


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValidationFailed.for_field("name", "不能为空", _NAME_LABEL)
    if len(cleaned) > _NAME_MAX_LENGTH:
        raise ValidationFailed.for_field("name", "超出范围", _NAME_LABEL)
    return cleaned


class TagService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_with_counts(self) -> list[tuple[Tag, int]]:
        """一次 LEFT JOIN + GROUP BY，算出每个标签的使用数（含 0）。"""
        rows = self._session.execute(
            select(Tag, func.count(mistake_tag.c.mistake_id))
            .outerjoin(mistake_tag, mistake_tag.c.tag_id == Tag.id)
            .group_by(Tag.id)
            .order_by(Tag.name)
        )
        return [(tag, count) for tag, count in rows]

    def _count(self, tag_id: int) -> int:
        return (
            self._session.scalar(
                select(func.count()).select_from(mistake_tag).where(mistake_tag.c.tag_id == tag_id)
            )
            or 0
        )

    def rename(self, tag_id: int, name: str) -> tuple[Tag, int]:
        tag = self._session.get(Tag, tag_id)
        if tag is None:
            raise NotFoundError("标签不存在")
        cleaned = _clean_name(name)
        if cleaned != tag.name:
            duplicate = self._session.scalar(
                select(Tag.id).where(Tag.name == cleaned, Tag.id != tag.id)
            )
            if duplicate is not None:
                raise ConflictError("标签已存在")
            tag.name = cleaned
            try:
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise ConflictError("标签已存在") from None
        return tag, self._count(tag.id)

    def delete(self, tag_id: int) -> None:
        tag = self._session.get(Tag, tag_id)
        if tag is None:
            raise NotFoundError("标签不存在")
        try:
            # tag_id 的外键没有级联：先解除关联，再删标签，同一事务
            self._session.execute(mistake_tag.delete().where(mistake_tag.c.tag_id == tag_id))
            self._session.delete(tag)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
