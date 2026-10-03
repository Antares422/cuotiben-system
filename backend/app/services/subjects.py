from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError
from app.models import Subject

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
