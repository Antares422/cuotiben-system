from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.ocr.base import OcrEngine
from app.services.images import ImageService
from app.services.mistakes import Clock, MistakeService
from app.services.subjects import SubjectService
from app.services.uploads import UploadService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_ocr_engine(request: Request) -> OcrEngine:
    return request.app.state.ocr_engine


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SettingsDep = Annotated[Settings, Depends(get_settings)]
OcrEngineDep = Annotated[OcrEngine, Depends(get_ocr_engine)]
SessionDep = Annotated[Session, Depends(get_session)]


def get_subject_service(session: SessionDep) -> SubjectService:
    return SubjectService(session)


def get_image_service(settings: SettingsDep) -> ImageService:
    return ImageService(settings.data_dir)


ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]


def get_upload_service(
    images: ImageServiceDep, ocr_engine: OcrEngineDep, settings: SettingsDep
) -> UploadService:
    return UploadService(images, ocr_engine, settings.max_upload_mb)


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


ClockDep = Annotated[Clock, Depends(get_clock)]


def get_mistake_service(
    session: SessionDep, clock: ClockDep, images: ImageServiceDep
) -> MistakeService:
    return MistakeService(session, clock, images)


MistakeServiceDep = Annotated[MistakeService, Depends(get_mistake_service)]
SubjectServiceDep = Annotated[SubjectService, Depends(get_subject_service)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
