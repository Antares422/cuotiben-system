from dataclasses import asdict

from fastapi import APIRouter, UploadFile

from app.api.deps import UploadServiceDep
from app.errors import BadRequestError
from app.schemas import Envelope, OcrOut, UploadOut, created

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("", status_code=201, response_model=Envelope[UploadOut])
def upload_image(service: UploadServiceDep, file: UploadFile | None = None) -> dict:
    if file is None:
        raise BadRequestError("请选择要上传的图片")
    # 多读 1 字节用于判断是否超限，避免把超大文件整个读进内存
    content = file.file.read(service.max_bytes + 1)
    image_id, result = service.handle(content)
    return created(
        UploadOut(
            image_id=image_id,
            image_url=f"/api/images/{image_id}",
            ocr=OcrOut(**asdict(result)),
        )
    )
