from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import MistakeServiceDep
from app.schemas import (
    Envelope,
    MasteryUpdate,
    MistakeCreate,
    MistakeOut,
    MistakeUpdate,
    Page,
    created,
    ok,
)

router = APIRouter(prefix="/api/mistakes", tags=["mistakes"])


@router.get("", response_model=Envelope[Page[MistakeOut]])
def list_mistakes(
    service: MistakeServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    subject_id: Annotated[int | None, Query()] = None,
    tag: Annotated[list[str] | None, Query()] = None,
    mastery_min: Annotated[int | None, Query(ge=1, le=5)] = None,
    mastery_max: Annotated[int | None, Query(ge=1, le=5)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> dict:
    items, total, overall_total = service.list_page(
        page=page,
        page_size=page_size,
        subject_id=subject_id,
        tags=tag or [],
        mastery_min=mastery_min,
        mastery_max=mastery_max,
        q=q,
    )
    return ok(
        {
            "items": [MistakeOut.from_model(m) for m in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "overall_total": overall_total,
        }
    )


@router.patch("/{mistake_id}", response_model=Envelope[MistakeOut])
def update_mistake(mistake_id: int, body: MistakeUpdate, service: MistakeServiceDep) -> dict:
    mistake = service.update(
        mistake_id,
        content=body.content,
        subject_id=body.subject_id,
        answer=body.answer,
        error_reason=body.error_reason,
        tags=body.tags,
        image_id=body.image_id,
    )
    return ok(MistakeOut.from_model(mistake))


@router.delete("/{mistake_id}", response_model=Envelope[None])
def delete_mistake(mistake_id: int, service: MistakeServiceDep) -> dict:
    service.delete(mistake_id)
    return ok()


@router.put("/{mistake_id}/mastery", response_model=Envelope[MistakeOut])
def set_mastery(mistake_id: int, body: MasteryUpdate, service: MistakeServiceDep) -> dict:
    mistake = service.set_mastery(mistake_id, body.level)
    return ok(MistakeOut.from_model(mistake))


@router.get("/{mistake_id}", response_model=Envelope[MistakeOut])
def get_mistake(mistake_id: int, service: MistakeServiceDep) -> dict:
    return ok(MistakeOut.from_model(service.get(mistake_id)))


@router.post("", status_code=201, response_model=Envelope[MistakeOut])
def create_mistake(body: MistakeCreate, service: MistakeServiceDep) -> dict:
    mistake = service.create(
        content=body.content,
        subject_id=body.subject_id,
        answer=body.answer,
        error_reason=body.error_reason,
        tags=body.tags,
        image_id=body.image_id,
    )
    return created(MistakeOut.from_model(mistake))
