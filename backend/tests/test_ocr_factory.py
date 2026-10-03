import pytest
from pydantic import ValidationError

from app.config import Settings
from app.main import build_ocr_engine
from app.ocr.fake import FakeOcrEngine
from app.ocr.rapid import RapidOcrEngine


def test_fake_engine_is_built_when_configured() -> None:
    assert isinstance(build_ocr_engine(Settings(ocr_engine="fake")), FakeOcrEngine)


def test_rapidocr_engine_is_built_with_the_configured_model_tier() -> None:
    engine = build_ocr_engine(Settings(ocr_engine="rapidocr", ocr_model_tier="tiny"))

    assert isinstance(engine, RapidOcrEngine)
    assert engine.model_tier == "tiny"


def test_model_tier_defaults_to_small() -> None:
    assert Settings().ocr_model_tier == "small"


def test_unknown_model_tier_is_rejected_at_startup() -> None:
    with pytest.raises(ValidationError):
        Settings(ocr_model_tier="huge")
