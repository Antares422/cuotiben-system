from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationFailed
from app.models import Mistake, Subject

_NAME_LABEL = "学科名称"
_NAME_MAX_LENGTH = 50

DEFAULT_SUBJECTS = ["语文", "数学", "英语", "物理", "化学", "生物", "政治", "历史", "地理"]


class SubjectService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def seed_defaults(self) -> None:
        if self._session.scalar(select(Subject.id).limit(1)) is not None:
            return
        self._session.add_all(Subject(name=name) for name in DEFAULT_SUBJECTS)
        self._session.commit()

    def create(self, name: str) -> Subject:
        subject = Subject(name=name)
        self._session.add(subject)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise ConflictError("学科已存在") from None
        return subject

    def list_all(self) -> list[Subject]:
        return list(self._session.scalars(select(Subject).order_by(Subject.id)))

    def list_with_counts(self) -> list[tuple[Subject, int]]:
        """一次 LEFT JOIN + GROUP BY，算出每个学科下的错题数（含 0）。"""
        rows = self._session.execute(
            select(Subject, func.count(Mistake.id))
            .outerjoin(Mistake, Mistake.subject_id == Subject.id)
            .group_by(Subject.id)
            .order_by(Subject.id)
        )
        return [(subject, count) for subject, count in rows]

    def rename(self, subject_id: int, name: str) -> tuple[Subject, int]:
        subject = self._session.get(Subject, subject_id)
        if subject is None:
            raise NotFoundError("学科不存在")
        cleaned = name.strip()
        if not cleaned:
            raise ValidationFailed.for_field("name", "不能为空", _NAME_LABEL)
        if len(cleaned) > _NAME_MAX_LENGTH:
            raise ValidationFailed.for_field("name", "超出范围", _NAME_LABEL)
        if cleaned != subject.name:
            duplicate = self._session.scalar(
                select(Subject.id).where(Subject.name == cleaned, Subject.id != subject.id)
            )
            if duplicate is not None:
                raise ConflictError("学科已存在")
            subject.name = cleaned
            try:
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                raise ConflictError("学科已存在") from None
        count = (
            self._session.scalar(
                select(func.count()).select_from(Mistake).where(Mistake.subject_id == subject.id)
            )
            or 0
        )
        return subject, count

    def delete(self, subject_id: int) -> None:
        subject = self._session.get(Subject, subject_id)
        if subject is None:
            raise NotFoundError("学科不存在")
        count = (
            self._session.scalar(
                select(func.count()).select_from(Mistake).where(Mistake.subject_id == subject_id)
            )
            or 0
        )
        if count > 0:
            raise ConflictError(
                f"该学科下还有 {count} 道错题，请先处理这些错题",
                {"mistake_count": count},
            )
        self._session.delete(subject)
        self._session.commit()
