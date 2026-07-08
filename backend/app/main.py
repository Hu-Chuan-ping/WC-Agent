import sys
sys.stdout.reconfigure(encoding="utf-8")

import asyncio
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.prediction import router as prediction_router
from app.api.v1.user import router as user_router
from app.core.eval.resolver import resolve_pending
from app.infra.db import schema
from app.infra.db.mysql_client import close_pool
from app.infra.db.redis_client import close_redis
from app.utils.exceptions import AppError
from app.utils.logger import logger

_RESOLVE_INTERVAL = 1800  # 定时结算间隔（秒）：30 分钟


async def _periodic_resolve() -> None:
    """后台定时结算已结束的比赛。"""
    while True:
        await asyncio.sleep(_RESOLVE_INTERVAL)
        try:
            await resolve_pending()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("定时结算失败")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await schema.ensure_all_tables()   # MySQL：user_profile + predictions 表
    try:
        await resolve_pending()       # 启动补扫：把关机期间结束的比赛补算
    except Exception:
        logger.exception("启动补扫结算失败")
    task = asyncio.create_task(_periodic_resolve())
    yield
    # 关闭时停后台任务、释放连接
    task.cancel()
    await close_redis()
    await close_pool()


app = FastAPI(title="WC Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段全放行，上线前收紧
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(prediction_router, prefix="/api/v1", tags=["prediction"])
app.include_router(user_router, prefix="/api/v1", tags=["user"])


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """给每个请求生成 request_id，记录进出与耗时；contextualize 让下游所有日志自动带上该 id。"""
    request_id = uuid.uuid4().hex[:8]
    with logger.contextualize(request_id=request_id):
        logger.info(f"→ {request.method} {request.url.path}")
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"← {request.method} {request.url.path} {response.status_code} {elapsed_ms:.0f}ms")
        response.headers["X-Request-ID"] = request_id
        return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """统一接住所有业务异常，翻译成 {code, message} 规范响应，并记录日志。"""
    msg = f"业务异常 code={exc.code} {exc.message}"
    if exc.detail:
        msg += f" | detail={exc.detail}"
    # 4xxx 多为调用方问题用 warning；5xxx 为服务端问题用 error（含堆栈）
    if exc.http_status < 500:
        logger.warning(msg)
    else:
        logger.opt(exception=exc).error(msg)
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


@app.get("/health")
def health():
    return {"status": "ok"}
