from fastapi import APIRouter

from app.api.deps import SubjectServiceDep
from app.schemas import Envelope, ItemList, SubjectCreate, SubjectOut, created, ok

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


@router.get("", response_model=Envelope[ItemList[SubjectOut]])
def list_subjects(service: SubjectServiceDep) -> dict:
    items = service.list_all()
    return ok({"items": [SubjectOut.model_validate(s) for s in items]})


@router.post("", status_code=201, response_model=Envelope[SubjectOut])
def create_subject(body: SubjectCreate, service: SubjectServiceDep) -> dict:
    return created(SubjectOut.model_validate(service.create(body.name)))
