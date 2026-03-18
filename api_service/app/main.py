from __future__ import annotations

import asyncio
import json

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import log_audit
from .cache import get_redis_client
from .config import load_settings
from .db import get_engine, get_session_factory, metadata
from .feature_store import fetch_features
from .observability import metrics_middleware
from .scoring import explain_features, load_model, score_features
from .schemas import BatchScoreRequest, BatchScoreResponse, ScoreResponse
from .security import init_settings, security_dependency


settings = load_settings()
init_settings(settings)

app = FastAPI(title="Trust Score Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Agent-Id",
        "X-Agent-Signature",
        "X-Agent-Skill",
        "X-Agent-Vetted",
    ],
)

app.middleware("http")(metrics_middleware)


@app.middleware("http")
async def tls_enforcer(request: Request, call_next):
    if settings.enforce_tls:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        if proto != "https":
            return Response(status_code=403, content="TLS required")
    return await call_next(request)


@app.on_event("startup")
async def on_startup():
    app.state.engine = get_engine(settings.db_url)
    app.state.session_factory = get_session_factory(app.state.engine)
    app.state.redis = get_redis_client(settings.redis_url)
    app.state.model = load_model(
        settings.model_onnx_path, settings.model_features_path, settings.model_feature_importance_path
    )

    async with app.state.engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


@app.on_event("shutdown")
async def on_shutdown():
    await app.state.redis.close()
    await app.state.engine.dispose()


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/oauth/token")
async def oauth_token_template(form_data: OAuth2PasswordRequestForm = Depends()):
    # Template endpoint: use external OAuth2 provider in production.
    raise HTTPException(
        status_code=501,
        detail=(
            "Token issuer template only. Configure your OAuth2 provider and pass bearer tokens "
            "to this API. Use api_service/scripts/generate_tokens.py only for local development."
        ),
    )


async def _get_session(request: Request) -> AsyncSession:
    async_session = request.app.state.session_factory
    async with async_session() as session:
        yield session


@app.get("/score/{institution_id}", response_model=ScoreResponse)
async def score_institution(
    institution_id: str,
    request: Request,
    token=Depends(security_dependency),
    session: AsyncSession = Depends(_get_session),
):
    cache_key = f"score:{institution_id}"
    cached = await request.app.state.redis.get(cache_key)
    if cached:
        payload = json.loads(cached)
        return ScoreResponse(**payload)

    features = await fetch_features(session, institution_id)
    if not features:
        raise HTTPException(status_code=404, detail="Features not found")

    score = score_features(request.app.state.model, features)
    explanation = explain_features(request.app.state.model, features)

    response = ScoreResponse(institution_id=institution_id, trust_score=score, explanation=explanation)
    await request.app.state.redis.setex(cache_key, settings.cache_ttl_sec, response.model_dump_json())

    await log_audit(
        session,
        actor=token.subject,
        action="score",
        resource=institution_id,
        details={"client_id": token.client_id, "path": "/score/{institution_id}"},
    )

    return response


@app.post("/batch/score", response_model=BatchScoreResponse)
async def batch_score(
    payload: BatchScoreRequest,
    request: Request,
    token=Depends(security_dependency),
    session: AsyncSession = Depends(_get_session),
):
    async def _score_item(item):
        features = item.features
        if features is None:
            features = await fetch_features(session, item.institution_id)
        if not features:
            return None
        score = score_features(request.app.state.model, features)
        explanation = explain_features(request.app.state.model, features)
        return ScoreResponse(
            institution_id=item.institution_id,
            trust_score=score,
            explanation=explanation,
        )

    tasks = [_score_item(item) for item in payload.items]
    results = [res for res in await asyncio.gather(*tasks) if res is not None]

    await log_audit(
        session,
        actor=token.subject,
        action="batch_score",
        resource="batch",
        details={"client_id": token.client_id, "count": len(results)},
    )

    return BatchScoreResponse(results=results)
