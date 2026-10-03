from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.models import Mistake

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """统一响应结构，code 与 HTTP 状态码相同。"""

    code: int
    message: str
    data: T | None = None


class ItemList(BaseModel, Generic[T]):
    items: list[T]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def ok(data: object = None) -> dict:
    return {"code": 200, "message": "ok", "data": data}


def created(data: object = None) -> dict:
    return {"code": 201, "message": "created", "data": data}


class OcrOut(BaseModel):
    status: str
    text: str
    message: str | None = None


class UploadOut(BaseModel):
    image_id: str
    image_url: str
    ocr: OcrOut


class MistakeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1)
    subject_id: int
    answer: str | None = None
    error_reason: str | None = None
    tags: list[str] = []
    image_id: str | None = None


class MistakeOut(BaseModel):
    id: int
    content: str
    answer: str | None
    error_reason: str | None
    subject: "SubjectOut"
    tags: list[str]
    image_id: str | None
    image_url: str | None
    mastered: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, mistake: "Mistake") -> "MistakeOut":
        return cls(
            id=mistake.id,
            content=mistake.content,
            answer=mistake.answer,
            error_reason=mistake.error_reason,
            subject=SubjectOut.model_validate(mistake.subject),
            tags=sorted(t.name for t in mistake.tags),  # 按名称排序，输出顺序才确定
            image_id=mistake.image_id,
            image_url=f"/api/images/{mistake.image_id}" if mistake.image_id else None,
            mastered=mistake.mastered,
            created_at=mistake.created_at,
            updated_at=mistake.updated_at,
        )


class SubjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
