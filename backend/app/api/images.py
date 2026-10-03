import mimetypes

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import ImageServiceDep

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{image_id}")
def get_image(image_id: str, service: ImageServiceDep) -> FileResponse:
    path = service.find(image_id)
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0])
