import logging
from collections.abc import Callable, Sequence

from app.ocr.base import OcrResult

logger = logging.getLogger(__name__)

RecognizeFn = Callable[[bytes], Sequence[str]]
Loader = Callable[[str], RecognizeFn]


def load_rapidocr(model_tier: str) -> RecognizeFn:
    """真正加载 RapidOCR（PP-OCRv6）。rapidocr 只在这里导入，没装可选依赖时也不影响其他功能。"""
    from rapidocr import ModelType, OCRVersion, RapidOCR

    tier = ModelType(model_tier)
    engine = RapidOCR(
        params={
            "Global.log_level": "warning",
            "Det.ocr_version": OCRVersion.PPOCRV6,
            "Det.model_type": tier,
            "Rec.ocr_version": OCRVersion.PPOCRV6,
            "Rec.model_type": tier,
        }
    )

    def recognize(image_bytes: bytes) -> Sequence[str]:
        return engine(image_bytes).txts or ()

    return recognize


class RapidOcrEngine:
    def __init__(self, model_tier: str = "small", loader: Loader = load_rapidocr) -> None:
        self.model_tier = model_tier
        self._loader = loader
        self._recognize_lines: RecognizeFn | None = None

    def recognize(self, image_bytes: bytes) -> OcrResult:
        # OcrEngine 的契约：任何失败都转成 status="failed"，绝不向外抛异常
        try:
            lines = [line for line in self._ensure_loaded()(image_bytes) if line.strip()]
        except Exception:
            logger.exception("RapidOCR failed")
            return OcrResult(status="failed", text="", message="文字识别失败，请手动输入")
        if not lines:
            return OcrResult(status="empty", text="", message="未识别到文字，请手动输入")
        return OcrResult(status="ok", text="\n".join(lines))

    def _ensure_loaded(self) -> RecognizeFn:
        # 模型在首次识别时才加载，避免拖慢应用启动；加载失败不缓存，下次会重试
        if self._recognize_lines is None:
            self._recognize_lines = self._loader(self.model_tier)
        return self._recognize_lines
