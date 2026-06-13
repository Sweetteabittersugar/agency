"""
统一 API 错误类型。
使用方式（新路由推荐）:
    from maestro.api_errors import invalid_input, not_found
    raise invalid_input("name", "名称不能为空")

现有路由（return True 模式）继续正常工作，逐步迁移。
"""


class AppError(Exception):
    """应用级异常，会被错误中间件捕获"""

    def __init__(self, code: str, message: str, http_status: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        super().__init__(message)


def bad_request(msg: str, **kwargs) -> AppError:
    return AppError("BAD_REQUEST", msg, 400, kwargs)


def not_found(resource: str, identifier: str = "") -> AppError:
    msg = f"{resource} 不存在" + (f": {identifier}" if identifier else "")
    return AppError("NOT_FOUND", msg, 404)


def permission_denied(msg: str = "权限不足") -> AppError:
    return AppError("PERMISSION_DENIED", msg, 403)


def invalid_input(field: str, reason: str = "") -> AppError:
    msg = f"参数无效: {field}" + (f" — {reason}" if reason else "")
    return AppError("INVALID_INPUT", msg, 400)


def internal_error(msg: str = "服务器内部错误") -> AppError:
    return AppError("INTERNAL_ERROR", msg, 500)


def handle_app_error(handler, error: AppError):
    """在路由处理函数中捕获 AppError 并返回统一格式"""
    handler.send_json(
        {
            "ok": False,
            "error": {"code": error.code, "message": error.message, "details": error.details},
        },
        error.http_status,
    )
