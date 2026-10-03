import pytest

from app.ocr.base import OcrResult
from app.ocr.rapid import RapidOcrEngine


def test_model_loads_lazily_on_first_recognize_and_only_once() -> None:
    loads: list[str] = []

    def loader(tier: str):
        loads.append(tier)
        return lambda image_bytes: ["第一行"]

    engine = RapidOcrEngine(model_tier="small", loader=loader)
    assert loads == []  # 构造函数里不能加载模型

    engine.recognize(b"image-1")
    engine.recognize(b"image-2")

    assert loads == ["small"]


def test_recognized_lines_are_joined_with_newlines() -> None:
    engine = RapidOcrEngine(loader=lambda tier: lambda image_bytes: ["已知 f(x)=x²", "求 f(2)"])

    assert engine.recognize(b"image") == OcrResult(status="ok", text="已知 f(x)=x²\n求 f(2)")


@pytest.mark.parametrize("lines", [[], [""], ["  ", ""]], ids=["none", "empty-string", "blanks"])
def test_no_recognized_text_is_reported_as_empty(lines) -> None:
    engine = RapidOcrEngine(loader=lambda tier: lambda image_bytes: lines)

    assert engine.recognize(b"image") == OcrResult(
        status="empty", text="", message="未识别到文字，请手动输入"
    )


FAILED = OcrResult(status="failed", text="", message="文字识别失败，请手动输入")


def test_recognition_error_is_reported_as_failed_instead_of_raised() -> None:
    def explode(image_bytes: bytes):
        raise RuntimeError("onnx crashed")

    engine = RapidOcrEngine(loader=lambda tier: explode)

    assert engine.recognize(b"image") == FAILED


def test_failed_model_load_is_reported_as_failed_and_retried_next_time() -> None:
    attempts = 0

    def flaky_loader(tier: str):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("model download interrupted")
        return lambda image_bytes: ["恢复正常"]

    engine = RapidOcrEngine(loader=flaky_loader)

    assert engine.recognize(b"image") == FAILED
    assert engine.recognize(b"image") == OcrResult(status="ok", text="恢复正常")
