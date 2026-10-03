from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import MistakeServiceDep
from app.schemas import Envelope, MistakeCreate, MistakeOut, Page, created, ok

router = APIRouter(prefix="/api/mistakes", tags=["mistakes"])


@router.get("", response_model=Envelope[Page[MistakeOut]])
def list_mistakes(
    service: MistakeServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    items, total = service.list_page(page=page, page_size=page_size)
    return ok(
        {
            "items": [MistakeOut.from_model(m) for m in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


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
