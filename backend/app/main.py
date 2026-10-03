from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from app import models  # noqa: F401  确保所有表在建表前已注册
from app.api import images, mistakes, subjects, uploads
from app.config import Settings
from app.db import Base, make_engine, make_session_factory
from app.errors import register_exception_handlers
from app.frontend import mount_frontend
from app.ocr.base import OcrEngine
from app.ocr.fake import FakeOcrEngine
from app.ocr.rapid import RapidOcrEngine
from app.services.mistakes import Clock
from app.services.subjects import SubjectService


def build_ocr_engine(settings: Settings) -> OcrEngine:
    if settings.ocr_engine == "fake":
        return FakeOcrEngine()
    if settings.ocr_engine == "rapidocr":
        return RapidOcrEngine(model_tier=settings.ocr_model_tier)
    raise ValueError(f"未知的 OCR 引擎: {settings.ocr_engine}")


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_app(
    settings: Settings | None = None,
    ocr_engine: OcrEngine | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.data_dir)
        Base.metadata.create_all(engine)
        app.state.settings = settings
        app.state.ocr_engine = ocr_engine or build_ocr_engine(settings)
        app.state.clock = clock or utc_now
        app.state.session_factory = make_session_factory(engine)
        with app.state.session_factory() as session:
            SubjectService(session).seed_defaults()
        yield
        engine.dispose()

    app = FastAPI(lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(subjects.router)
    app.include_router(uploads.router)
    app.include_router(images.router)
    app.include_router(mistakes.router)
    if settings.static_dir is not None:
        mount_frontend(app, settings.static_dir)
    return app
