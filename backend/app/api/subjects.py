from fastapi import APIRouter

from app.api.deps import SubjectServiceDep
from app.schemas import Envelope, ItemList, NameUpdate, SubjectCreate, SubjectOut, created, ok

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


@router.get("", response_model=Envelope[ItemList[SubjectOut]])
def list_subjects(service: SubjectServiceDep) -> dict:
    items = [
        SubjectOut(id=s.id, name=s.name, mistake_count=n) for s, n in service.list_with_counts()
    ]
    return ok({"items": items})


@router.post("", status_code=201, response_model=Envelope[SubjectOut])
def create_subject(body: SubjectCreate, service: SubjectServiceDep) -> dict:
    return created(SubjectOut.model_validate(service.create(body.name)))


@router.patch("/{subject_id}", response_model=Envelope[SubjectOut])
def rename_subject(subject_id: int, body: NameUpdate, service: SubjectServiceDep) -> dict:
    subject, mistake_count = service.rename(subject_id, body.name)
    return ok({"id": subject.id, "name": subject.name, "mistake_count": mistake_count})


@router.delete("/{subject_id}", response_model=Envelope[None])
def delete_subject(subject_id: int, service: SubjectServiceDep) -> dict:
    service.delete(subject_id)
    return ok()
