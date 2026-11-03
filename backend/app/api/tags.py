from fastapi import APIRouter

from app.api.deps import TagServiceDep
from app.schemas import Envelope, ItemList, NameUpdate, TagOut, ok

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=Envelope[ItemList[TagOut]])
def list_tags(service: TagServiceDep) -> dict:
    items = [TagOut(id=t.id, name=t.name, mistake_count=n) for t, n in service.list_with_counts()]
    return ok({"items": items})


@router.patch("/{tag_id}", response_model=Envelope[TagOut])
def rename_tag(tag_id: int, body: NameUpdate, service: TagServiceDep) -> dict:
    tag, mistake_count = service.rename(tag_id, body.name)
    return ok({"id": tag.id, "name": tag.name, "mistake_count": mistake_count})


@router.delete("/{tag_id}", response_model=Envelope[None])
def delete_tag(tag_id: int, service: TagServiceDep) -> dict:
    service.delete(tag_id)
    return ok()
