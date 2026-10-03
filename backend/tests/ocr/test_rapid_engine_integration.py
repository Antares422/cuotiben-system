import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.ocr.rapid import RapidOcrEngine

# 需要真实的 RapidOCR 和模型（首次运行会下载），默认不跑：pytest -m integration
pytestmark = pytest.mark.integration


def _render(text: str) -> bytes:
    image = Image.new("RGB", (700, 140), "white")
    ImageDraw.Draw(image).text((30, 30), text, font=ImageFont.load_default(size=64), fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_real_rapidocr_reads_rendered_text() -> None:
    result = RapidOcrEngine(model_tier="tiny").recognize(_render("Hello OCR 123"))

    assert result.status == "ok"
    assert "Hello" in result.text
    assert "123" in result.text


def test_real_rapidocr_reports_empty_for_a_blank_image() -> None:
    result = RapidOcrEngine(model_tier="tiny").recognize(_render(""))

    assert result.status == "empty"
