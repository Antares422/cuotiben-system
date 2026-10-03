from app.ocr.base import OcrResult


class FakeOcrEngine:
    """测试和前端联调用的假引擎，永远返回预设结果。"""

    def __init__(self, result: OcrResult | None = None) -> None:
        self._result = result or OcrResult(status="ok", text="识别出的题目")

    def recognize(self, image_bytes: bytes) -> OcrResult:
        return self._result
