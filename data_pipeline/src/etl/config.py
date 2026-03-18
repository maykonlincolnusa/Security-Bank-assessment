import os
from dataclasses import dataclass
from datetime import date
from typing import List


def _split_csv(value: str) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    # Database
    db_url: str

    # S3/MinIO
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str
    s3_bucket: str
    s3_prefix: str
    s3_sse_kms_key_id: str

    # BCB
    bcb_series_ids: List[str]
    bcb_start_date: str

    # Open Banking (OAuth2)
    ob_token_url: str
    ob_base_url: str
    ob_client_id: str
    ob_client_secret: str
    ob_scope: str

    # Financial statements
    finstat_urls: List[str]
    finstat_rate_limit_sec: float

    # News
    news_api_base_url: str
    news_api_key: str
    news_query: str
    news_language: str

    # Security
    cve_api_base_url: str
    virustotal_api_base_url: str
    virustotal_api_key: str

    # General
    default_start_date: str


def load_settings() -> Settings:
    today = date.today().isoformat()

    return Settings(
        db_url=os.getenv("ETL_DB_URL", "postgresql+psycopg2://airflow:airflow@postgres:5432/airflow"),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://minio:9000"),
        s3_access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
        s3_secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
        s3_region=os.getenv("S3_REGION", "us-east-1"),
        s3_bucket=os.getenv("S3_BUCKET", "raw-data"),
        s3_prefix=os.getenv("S3_PREFIX", "raw"),
        s3_sse_kms_key_id=os.getenv("S3_SSE_KMS_KEY_ID", ""),
        bcb_series_ids=_split_csv(os.getenv("BCB_SERIES_IDS", "1,433")),
        bcb_start_date=os.getenv("BCB_START_DATE", "2000-01-01"),
        ob_token_url=os.getenv("OPEN_BANKING_TOKEN_URL", ""),
        ob_base_url=os.getenv("OPEN_BANKING_BASE_URL", ""),
        ob_client_id=os.getenv("OPEN_BANKING_CLIENT_ID", ""),
        ob_client_secret=os.getenv("OPEN_BANKING_CLIENT_SECRET", ""),
        ob_scope=os.getenv("OPEN_BANKING_SCOPE", "accounts"),
        finstat_urls=_split_csv(os.getenv("FINSTAT_URLS", "")),
        finstat_rate_limit_sec=float(os.getenv("FINSTAT_RATE_LIMIT_SEC", "2")),
        news_api_base_url=os.getenv("NEWS_API_BASE_URL", ""),
        news_api_key=os.getenv("NEWS_API_KEY", ""),
        news_query=os.getenv("NEWS_QUERY", "banco OR instituicao financeira OR fintech"),
        news_language=os.getenv("NEWS_LANGUAGE", "pt"),
        cve_api_base_url=os.getenv("CVE_API_BASE_URL", "https://services.nvd.nist.gov/rest/json/cves/2.0"),
        virustotal_api_base_url=os.getenv("VT_API_BASE_URL", "https://www.virustotal.com/api/v3"),
        virustotal_api_key=os.getenv("VT_API_KEY", ""),
        default_start_date=os.getenv("DEFAULT_START_DATE", today),
    )
