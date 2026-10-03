from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """所有可变配置都来自环境变量，见 backend/.env.example。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    ocr_engine: str = "rapidocr"  # rapidocr | fake
    # PP-OCRv6 模型档位：small 是准确率与速度的最佳折中，tiny 供低配机器使用，见 docs/ocr-engine-selection.md
    ocr_model_tier: Literal["tiny", "small", "medium"] = "small"
    max_upload_mb: int = 10
    # 前端构建产物目录（frontend/dist）。设置后由后端一并托管，一个进程一个端口即可运行
    static_dir: Path | None = None
    cors_origins: list[str] = []
