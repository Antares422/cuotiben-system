from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class OcrResult:
    status: Literal["ok", "empty", "failed"]
    text: str
    message: str | None = None


class OcrEngine(Protocol):
    """OCR 引擎适配器。实现必须自行捕获异常并返回 status="failed"，不得向外抛出。"""

    def recognize(self, image_bytes: bytes) -> OcrResult: ...
