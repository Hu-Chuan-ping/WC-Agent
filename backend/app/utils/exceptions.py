from __future__ import annotations


class AppError(Exception):
    """
    所有业务异常的基类（对应 Java 里你自定义的 BusinessException 基类）。

    每个异常自带三样东西：
      - code:        业务错误码。约定 4xxx = 客户端/请求问题，5xxx = 服务端问题。
      - http_status: 对应的 HTTP 状态码，给 FastAPI exception_handler 用。
      - message:     默认的、可返回给前端的错误信息；raise 时可覆盖。

    用法：
        raise LLMError()                      # 用默认 message
        raise LLMError("DeepSeek 超时")        # 覆盖 message（会返回给前端）
        raise ToolError(detail=str(exc))      # message 用默认，detail 只进日志

    划分维度是「出了什么事」，不是「谁抛的」——任何 service/agent/tool 都可按需抛同一个类。
    """

    code: int = 5000
    http_status: int = 500
    message: str = "服务内部错误"

    def __init__(self, message: str | None = None, *, detail: str | None = None):
        # message 给前端看；detail 给日志看（可能含敏感/技术细节，不返回前端）
        self.message = message or self.message
        self.detail = detail
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """统一的对外错误结构，exception_handler 会用它生成响应体。"""
        return {"code": self.code, "message": self.message}


# ── 客户端 / 请求类（4xxx）────────────────────────────────────────

class ValidationError(AppError):
    """请求参数不合法（pydantic 没拦住、但业务规则不通过的情况）。"""

    code = 4000
    http_status = 422
    message = "请求参数有误"


class IntentRouteError(AppError):
    """意图识别失败，或没有匹配的 agent 且无兜底。"""

    code = 4001
    http_status = 400
    message = "无法识别请求意图"


class AuthError(AppError):
    """鉴权失败：验证码错误、用户名或密码不对、令牌无效/过期等。"""

    code = 4010
    http_status = 401
    message = "身份验证失败"


# ── 服务端 / 内部类（5xxx）────────────────────────────────────────

class ConfigError(AppError):
    """配置缺失或错误，例如缺少 API key。"""

    code = 5000
    http_status = 500
    message = "服务配置错误"


class ToolError(AppError):
    """工具执行过程中的逻辑错误（参数不对、解析失败等）。"""

    code = 5001
    http_status = 500
    message = "工具执行失败"


class LLMError(AppError):
    """调用大模型（DeepSeek）失败：超时、限流、返回异常等。"""

    code = 5002
    http_status = 502
    message = "大模型调用失败"


class ExternalServiceError(AppError):
    """调用第三方外部服务失败，例如 Tavily 搜索的 HTTP 请求出错。"""

    code = 5003
    http_status = 502
    message = "外部服务调用失败"
