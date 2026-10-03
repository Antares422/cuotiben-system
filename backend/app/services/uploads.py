import logging

from app.errors import PayloadTooLargeError
from app.ocr.base import OcrEngine, OcrResult
from app.services.images import ImageService

logger = logging.getLogger(__name__)

_OCR_FAILED_MESSAGE = "文字识别失败，请手动输入"


class UploadService:
    """编排一次上传：校验大小 → 保存图片 → OCR 出题目草稿。"""

    def __init__(self, images: ImageService, ocr_engine: OcrEngine, max_upload_mb: int) -> None:
        self._images = images
        self._ocr_engine = ocr_engine
        self._max_upload_mb = max_upload_mb

    @property
    def max_bytes(self) -> int:
        return self._max_upload_mb * 1024 * 1024

    def handle(self, content: bytes) -> tuple[str, OcrResult]:
        if len(content) > self.max_bytes:
            raise PayloadTooLargeError(f"图片不能超过 {self._max_upload_mb} MB")
        image_id = self._images.save(content)
        return image_id, self._recognize_safely(content)

    def _recognize_safely(self, content: bytes) -> OcrResult:
        """OCR 失败不得阻断录入流程：任何异常都转成 status="failed"。"""
        try:
            return self._ocr_engine.recognize(content)
        except Exception:
            logger.exception("OCR engine raised")
            return OcrResult(status="failed", text="", message=_OCR_FAILED_MESSAGE)
