from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException


def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """托管前端构建产物，并让前端路由（如 /mistakes/5）刷新后仍能打开。必须在所有 API 路由之后注册。"""
    root = static_dir.resolve()
    index = root / "index.html"

    def serve_frontend(path: str, request: Request) -> FileResponse:
        # /api 下不存在的路径、以及任何非 GET 请求，都返回 JSON 的 404，不能被前端页面吞掉
        if request.method != "GET" or path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        # is_relative_to 防止 ../ 之类的路径穿越读到目录之外的文件
        if candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)

    app.add_api_route(
        "/{path:path}",
        serve_frontend,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
