import io
import re
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.errors import NotFoundError, UnsupportedMediaTypeError

_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
_UNSUPPORTED_MESSAGE = "仅支持 JPG、PNG、WebP 格式的图片"
_NOT_FOUND_MESSAGE = "图片不存在"
_IMAGE_ID_PATTERN = re.compile(r"[0-9a-f]{32}")


def _detect_extension(content: bytes) -> str:
    """按图片内容判断类型，不信任文件名和 Content-Type。"""
    try:
        with Image.open(io.BytesIO(content)) as image:
            image_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise UnsupportedMediaTypeError(_UNSUPPORTED_MESSAGE) from None
    if image_format not in _EXTENSIONS:
        raise UnsupportedMediaTypeError(_UNSUPPORTED_MESSAGE)
    return _EXTENSIONS[image_format]


class ImageService:
    def __init__(self, data_dir: Path) -> None:
        self._images_dir = data_dir / "images"

    def find(self, image_id: str) -> Path:
        path = self._locate(image_id)
        if path is None:
            raise NotFoundError(_NOT_FOUND_MESSAGE)
        return path

    def exists(self, image_id: str) -> bool:
        return self._locate(image_id) is not None

    def _locate(self, image_id: str) -> Path | None:
        # 先严格校验格式：既防路径穿越，也防 * ? 这类通配符命中别人的图片
        if not _IMAGE_ID_PATTERN.fullmatch(image_id):
            return None
        return next(self._images_dir.glob(f"{image_id}.*"), None)

    def save(self, content: bytes) -> str:
        """校验并保存图片，返回 32 位十六进制的 image_id。"""
        extension = _detect_extension(content)
        image_id = uuid.uuid4().hex
        self._images_dir.mkdir(parents=True, exist_ok=True)
        (self._images_dir / f"{image_id}.{extension}").write_bytes(content)
        return image_id
