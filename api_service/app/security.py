from __future__ import annotations

import hmac
import hashlib
from dataclasses import dataclass
from typing import List

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_429_TOO_MANY_REQUESTS

from .config import Settings, load_settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/oauth/token")


@dataclass
class TokenData:
    subject: str
    roles: List[str]
    client_id: str


def decode_token(token: str, settings: Settings) -> TokenData:
    if not token:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    return TokenData(
        subject=str(payload.get("sub", "")),
        roles=payload.get("roles", []),
        client_id=payload.get("client_id", payload.get("sub", "")),
    )


def require_roles(allowed: List[str]):
    async def dependency(
        token_str: str = Depends(oauth2_scheme),
        settings: Settings = Depends(get_settings),
    ) -> TokenData:
        token = decode_token(token_str, settings)
        if not set(token.roles).intersection(set(allowed)):
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Insufficient role")
        return token

    return dependency


async def rate_limit(request: Request, token: TokenData, settings: Settings):
    redis = request.app.state.redis
    key = f"rl:{token.client_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > settings.rate_limit_per_minute:
        raise HTTPException(status_code=HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")


async def validate_agent_headers(request: Request, settings: Settings) -> None:
    agent_id = request.headers.get("X-Agent-Id")
    if not agent_id:
        return

    if settings.agent_allowed_ids and agent_id not in settings.agent_allowed_ids:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Agent not allowed")

    skill_id = request.headers.get("X-Agent-Skill", "")
    vetted = request.headers.get("X-Agent-Vetted", "false").lower() == "true"
    if skill_id and skill_id in settings.agent_skill_blacklist:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Skill blacklisted")
    if settings.agent_skill_allowlist and skill_id not in settings.agent_skill_allowlist:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Skill not allowlisted")
    if skill_id and not vetted:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Skill not vetted")

    if not settings.agent_signing_secret:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Agent signature not configured")

    body = await request.body()
    msg = f"{agent_id}:{request.method}:{request.url.path}".encode("utf-8") + body
    expected = hmac.new(settings.agent_signing_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    signature = request.headers.get("X-Agent-Signature", "")
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid agent signature")


async def security_dependency(
    request: Request,
    token: TokenData = Depends(require_roles(["auditor", "analyst", "system"])),
    settings: Settings = Depends(get_settings),
) -> TokenData:
    await validate_agent_headers(request, settings)
    await rate_limit(request, token, settings)
    return token


_settings: Settings | None = None


def get_settings() -> Settings:
    if _settings is None:
        return load_settings()
    return _settings


def init_settings(settings: Settings) -> None:
    global _settings
    _settings = settings
