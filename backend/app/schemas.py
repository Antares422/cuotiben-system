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
    # 不受筛选影响的总数（仅错题列表响应设置，容量提醒用）
    overall_total: int | None = None


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


class SubjectBrief(BaseModel):
    """嵌在错题里的学科摘要：只含 id 与名称。"""

    id: int
    name: str


class MistakeOut(BaseModel):
    id: int
    content: str
    answer: str | None
    error_reason: str | None
    subject: "SubjectBrief"
    tags: list[str]
    image_id: str | None
    image_url: str | None
    mastery_level: int
    mastered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, mistake: "Mistake") -> "MistakeOut":
        return cls(
            id=mistake.id,
            content=mistake.content,
            answer=mistake.answer,
            error_reason=mistake.error_reason,
            subject=SubjectBrief(id=mistake.subject.id, name=mistake.subject.name),
            tags=sorted(t.name for t in mistake.tags),  # 按名称排序，输出顺序才确定
            image_id=mistake.image_id,
            image_url=f"/api/images/{mistake.image_id}" if mistake.image_id else None,
            mastery_level=mistake.mastery_level,
            mastered_at=mistake.mastered_at,
            created_at=mistake.created_at,
            updated_at=mistake.updated_at,
        )


class MasteryUpdate(BaseModel):
    level: int = Field(ge=1, le=5)


class MistakeUpdate(MistakeCreate):
    """编辑错题：字段与录入一致，校验规则相同。"""


class NameUpdate(BaseModel):
    """重命名学科/标签。空名与超长由服务层按资源给出中文提示（T033）。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str


class TagOut(BaseModel):
    id: int
    name: str
    mistake_count: int


class SubjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    mistake_count: int = 0
