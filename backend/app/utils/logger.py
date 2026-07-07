from __future__ import annotations

import functools
import sys
from pathlib import Path

from loguru import logger

from app.config.settings import settings

# 日志格式：时间 | 级别 | 请求ID | 位置 - 消息
_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[request_id]}</cyan> | "
    "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
)

_configured = False


def setup_logger() -> None:
    """配置 loguru：控制台 + （可选）D 盘按天轮转的文件。幂等，可重复调用。"""
    global _configured
    if _configured:
        return

    logger.remove()  # 去掉 loguru 默认 handler
    # 设默认 request_id，未绑定时显示 "-"，避免格式里取不到 extra 报错
    logger.configure(extra={"request_id": "-"})

    # loguru 写 stderr，Windows 下默认 gbk 会让中文/emoji 乱码 → 强制 utf-8
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # 控制台
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=_FORMAT,
        enqueue=True,        # 异步/多线程安全
        backtrace=True,      # 异常时显示完整调用链
        diagnose=False,      # 但不打印每帧变量值：太吵 + 可能泄露密钥
    )

    # 文件（写到 D 盘）
    if settings.log_to_file:
        Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
        logger.add(
            str(Path(settings.log_dir) / "wc-agent_{time:YYYY-MM-DD}.log"),
            level=settings.log_level,
            format=_FORMAT,
            rotation="00:00",      # 每天午夜切新文件
            retention="14 days",   # 旧日志保留 14 天后自动删
            encoding="utf-8",
            enqueue=True,
            backtrace=True,        # 异常时记录完整调用链
            diagnose=False,        # 生产关掉：避免把变量值（可能含密钥）写进日志
        )

    _configured = True


def logged(func):
    """
    给「异步方法」加调用日志的装饰器（你问的 Java 切面/注解的 Python 版）。

    进入时记录方法名，正常返回记录完成，抛异常记录失败后原样上抛。
    注意：被装饰对象是 async 方法，所以 wrapper 也必须 async + await。
    """

    @functools.wraps(func)  # 保留原函数名/docstring，否则 FastAPI、调试会出问题
    async def wrapper(*args, **kwargs):
        name = func.__qualname__  # 形如 DispatchService.dispatch
        logger.info(f"▶ 调用 {name}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"✔ 完成 {name}")
            return result
        except Exception as exc:
            logger.error(f"✘ 失败 {name}: {exc}")
            raise

    return wrapper


# 模块被导入即完成配置，任何 `from app.utils.logger import logger` 都拿到配好的 logger
setup_logger()

__all__ = ["logger", "logged", "setup_logger"]
