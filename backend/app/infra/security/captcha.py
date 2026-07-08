from __future__ import annotations

import base64
import random
import string
import uuid

from captcha.image import ImageCaptcha

from app.config.settings import settings
from app.infra.db.redis_client import get_redis

# 图形验证码：生成一张 4 位字符的 PNG，答案存 Redis(captcha:{id})，带 TTL。
# 图片(含 id)发给前端，答案只留服务端；校验时一次性取用并删除。

_ALPHABET = string.ascii_uppercase + string.digits  # 大写字母+数字，避免易混淆的小写
_LENGTH = 4
_image = ImageCaptcha(width=160, height=60)


def _key(captcha_id: str) -> str:
    return f"captcha:{captcha_id}"


async def generate() -> tuple[str, str]:
    """生成一个验证码。返回 (captcha_id, data_uri)，data_uri 可直接塞进 <img src>。"""
    text = "".join(random.choices(_ALPHABET, k=_LENGTH))
    captcha_id = uuid.uuid4().hex

    png_bytes = _image.generate(text).getvalue()
    data_uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")

    # 存答案（大写归一），设过期
    await get_redis().set(_key(captcha_id), text, ex=settings.captcha_ttl_seconds)
    return captcha_id, data_uri


async def verify(captcha_id: str, text: str) -> bool:
    """校验用户输入。命中即删除（一次性使用，防重放）。大小写不敏感。"""
    if not captcha_id or not text:
        return False
    r = get_redis()
    answer = await r.get(_key(captcha_id))
    if answer is None:
        return False
    await r.delete(_key(captcha_id))
    return text.strip().upper() == answer.upper()
