import os
from dataclasses import dataclass
from typing import List


def _split_csv(value: str) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    db_url: str
    redis_url: str
    model_onnx_path: str
    model_features_path: str
    model_feature_importance_path: str

    jwt_secret: str
    jwt_issuer: str
    jwt_audience: str
    enforce_tls: bool
    cors_origins: List[str]
    rate_limit_per_minute: int
    cache_ttl_sec: int

    agent_signing_secret: str
    agent_allowed_ids: List[str]
    agent_skill_blacklist: List[str]
    agent_skill_allowlist: List[str]



def load_settings() -> Settings:
    return Settings(
        db_url=os.getenv("SERVICE_DB_URL", "postgresql+asyncpg://service:service@postgres:5432/service"),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        model_onnx_path=os.getenv("MODEL_ONNX_PATH", "models/output/model.onnx"),
        model_features_path=os.getenv("MODEL_FEATURES_PATH", "models/output/model_features.json"),
        model_feature_importance_path=os.getenv("MODEL_FEATURE_IMPORTANCE_PATH", ""),
        jwt_secret=os.getenv("JWT_SECRET", "change-me"),
        jwt_issuer=os.getenv("JWT_ISSUER", "trust-score-service"),
        jwt_audience=os.getenv("JWT_AUDIENCE", "trust-score-clients"),
        enforce_tls=os.getenv("ENFORCE_TLS", "false").lower() == "true",
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS", "http://localhost:3000")),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        cache_ttl_sec=int(os.getenv("CACHE_TTL_SEC", "300")),
        agent_signing_secret=os.getenv("AGENT_SIGNING_SECRET", ""),
        agent_allowed_ids=_split_csv(os.getenv("AGENT_ALLOWED_IDS", "")),
        agent_skill_blacklist=_split_csv(os.getenv("AGENT_SKILL_BLACKLIST", "")),
        agent_skill_allowlist=_split_csv(os.getenv("AGENT_SKILL_ALLOWLIST", "")),
    )
