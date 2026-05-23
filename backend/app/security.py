import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Header, HTTPException


SECRET = os.getenv("APP_SECRET_KEY", "change_me")


# Кодирует байтовую строку в безопасный Base64-формат для токена
def _b64(value: bytes):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


# Создаёт токен доступа для авторизованного пользователя
def create_token(username: str):
    payload = {
        "sub": username,
        "exp": int(time.time())
        + int(os.getenv("JWT_EXPIRE_MINUTES", "480")) * 60,
    }

    body = _b64(
        json.dumps(
            payload,
            ensure_ascii=False,
        ).encode()
    )

    signature = _b64(
        hmac.new(
            SECRET.encode(),
            body.encode(),
            hashlib.sha256,
        ).digest()
    )

    return f"{body}.{signature}"


# Проверяет наличие, корректность подписи и срок действия токена
def verify_token(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Нет токена",
        )

    token = authorization.split(" ", 1)[1]

    try:
        body, signature = token.split(".", 1)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Некорректный токен",
        )

    expected_signature = _b64(
        hmac.new(
            SECRET.encode(),
            body.encode(),
            hashlib.sha256,
        ).digest()
    )

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=401,
            detail="Некорректная подпись",
        )

    payload = json.loads(
        base64.urlsafe_b64decode(
            body + "=" * (-len(body) % 4)
        )
    )

    if payload.get("exp", 0) < time.time():
        raise HTTPException(
            status_code=401,
            detail="Токен истек",
        )

    return payload["sub"]