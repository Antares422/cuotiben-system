from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UtcDateTime


class Subject(Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


mistake_tag = Table(
    "mistake_tag",
    Base.metadata,
    Column("mistake_id", ForeignKey("mistake.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Mistake(Base):
    __tablename__ = "mistake"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    error_reason: Mapped[str | None] = mapped_column(Text)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"))
    image_id: Mapped[str | None] = mapped_column(String(32))
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)

    subject: Mapped[Subject] = relationship()
    tags: Mapped[list[Tag]] = relationship(secondary=mistake_tag)
