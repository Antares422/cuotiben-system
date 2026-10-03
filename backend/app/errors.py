import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_DEFAULT_MESSAGES = {
    404: "资源不存在",
    405: "请求方法不允许",
}

# 字段名 -> 面向用户的中文名，用于拼接校验失败的提示
FIELD_LABELS = {
    "content": "题目内容",
    "name": "学科名称",
    "subject_id": "学科",
    "mistake_id": "错题编号",
    "page": "页码",
    "page_size": "每页数量",
}

_REQUIRED_TYPES = {"missing", "string_too_short"}
_OUT_OF_RANGE_TYPES = {"greater_than_equal", "less_than_equal", "greater_than", "less_than"}


def _field_message(error_type: str) -> str:
    if error_type in _REQUIRED_TYPES:
        return "不能为空"
    if error_type in _OUT_OF_RANGE_TYPES:
        return "超出范围"
    return "格式不正确"


def envelope(code: int, message: str, data: object = None) -> dict:
    """统一响应结构：code 必须等于 HTTP 状态码。"""
    return {"code": code, "message": message, "data": data}


class AppError(Exception):
    """业务错误基类。子类的 code 固定等于对应的 HTTP 状态码。"""

    code = 500

    def __init__(self, message: str, data: object = None) -> None:
        super().__init__(message)
        self.message = message
        self.data = data


class BadRequestError(AppError):
    code = 400


class ValidationFailed(AppError):
    """业务校验未通过（字段合法但取值不被接受，如引用了不存在的学科）。"""

    code = 422

    @classmethod
    def for_field(cls, field: str, reason: str, label: str) -> "ValidationFailed":
        return cls(f"{label}{reason}", {"fields": [{"field": field, "message": reason}]})


class NotFoundError(AppError):
    code = 404


class ConflictError(AppError):
    code = 409


class PayloadTooLargeError(AppError):
    code = 413


class UnsupportedMediaTypeError(AppError):
    code = 415


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.code, content=envelope(exc.code, exc.message, exc.data))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = _DEFAULT_MESSAGES.get(exc.status_code, str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=envelope(exc.status_code, message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        if any(err["type"] == "json_invalid" for err in exc.errors()):
            return JSONResponse(status_code=400, content=envelope(400, "请求格式不正确"))
        fields = [
            {"field": str(err["loc"][-1]), "message": _field_message(err["type"])}
            for err in exc.errors()
        ]
        first = fields[0]
        label = FIELD_LABELS.get(first["field"], first["field"])
        return JSONResponse(
            status_code=422,
            content=envelope(422, f"{label}{first['message']}", {"fields": fields}),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # 堆栈只写日志，不返回给客户端
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=envelope(500, "服务器开小差了，请稍后再试"))
