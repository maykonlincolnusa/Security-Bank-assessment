from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd

from .catalog import LineageRecord, write_lineage, write_schema
from .config import Settings
from .db import CheckpointStore, get_engine
from .storage import S3Storage
from .sources.bcb import fetch_bcb_series_bulk
from .sources.financials import fetch_financial_statements
from .sources.news import fetch_news
from .sources.open_banking import OpenBankingClient, normalize_open_banking_accounts, normalize_open_banking_balances
from .sources.security import fetch_cves, fetch_virustotal_iocs

RAW_SCHEMA = "raw"
STAGING_SCHEMA = "staging"
CURATED_SCHEMA = "curated"


@dataclass
class PipelineContext:
    settings: Settings
    storage: S3Storage
    checkpoint: CheckpointStore


def run_daily(settings: Settings) -> None:
    run_ingestion_only(settings)
    run_validate_schemas_only(settings)
    run_transform_only(settings)


def _build_context(settings: Settings) -> Tuple[PipelineContext, object]:
    engine = get_engine(settings.db_url)
    storage = S3Storage(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
        bucket=settings.s3_bucket,
        sse_kms_key_id=settings.s3_sse_kms_key_id,
    )
    checkpoint = CheckpointStore(engine)
    ctx = PipelineContext(settings=settings, storage=storage, checkpoint=checkpoint)
    return ctx, engine


def run_ingestion_only(settings: Settings) -> None:
    ctx, engine = _build_context(settings)
    bcb_df = ingest_bcb(ctx, engine)
    ingest_open_banking(ctx, engine)
    fin_df = ingest_financials(ctx, engine)
    news_df = ingest_news(ctx, engine)
    cve_df, vt_df = ingest_security(ctx, engine)

    if not bcb_df.empty:
        write_raw_snapshot(ctx, "bcb_series", bcb_df)
    if not news_df.empty:
        write_raw_snapshot(ctx, "news", news_df)
    if not fin_df.empty:
        write_raw_snapshot(ctx, "financial_statements", fin_df)
    if not cve_df.empty:
        write_raw_snapshot(ctx, "cves", cve_df)
    if not vt_df.empty:
        write_raw_snapshot(ctx, "virustotal", vt_df)


def run_validate_schemas_only(settings: Settings) -> None:
    ctx, engine = _build_context(settings)
    validate_raw_schemas(ctx, engine)


def run_transform_only(settings: Settings) -> None:
    ctx, engine = _build_context(settings)
    bank_dict = load_bank_dictionary()
    normalize_bcb(ctx, engine, safe_read_table(engine, RAW_SCHEMA, "bcb_series"))
    normalize_open_banking(
        ctx,
        engine,
        safe_read_table(engine, RAW_SCHEMA, "open_banking_accounts"),
        safe_read_table(engine, RAW_SCHEMA, "open_banking_balances"),
        bank_dict,
    )
    normalize_financials(ctx, engine, safe_read_table(engine, RAW_SCHEMA, "financial_statements"), bank_dict)
    normalize_news(ctx, engine, safe_read_table(engine, RAW_SCHEMA, "news"))
    normalize_security(
        ctx,
        engine,
        safe_read_table(engine, RAW_SCHEMA, "cves"),
        safe_read_table(engine, RAW_SCHEMA, "virustotal"),
    )

    curated_bcb(ctx, engine)
    curated_news(ctx, engine)
    curated_security(ctx, engine)


def ingest_bcb(ctx: PipelineContext, engine) -> pd.DataFrame:
    last = ctx.checkpoint.get("bcb") or ctx.settings.bcb_start_date
    df = fetch_bcb_series_bulk(ctx.settings.bcb_series_ids, start_date=last, end_date=None)
    if not df.empty:
        df["ref_date"] = pd.to_datetime(df["ref_date"]).dt.date
        load_dataframe(engine, df, RAW_SCHEMA, "bcb_series")
        ctx.checkpoint.set("bcb", df["ref_date"].max().isoformat())
        write_schema(ctx.storage, ctx.settings.s3_prefix, f"{RAW_SCHEMA}.bcb_series", df)
    return df


def ingest_open_banking(ctx: PipelineContext, engine) -> Tuple[pd.DataFrame, pd.DataFrame]:
    client = OpenBankingClient(
        ctx.settings.ob_token_url,
        ctx.settings.ob_base_url,
        ctx.settings.ob_client_id,
        ctx.settings.ob_client_secret,
        ctx.settings.ob_scope,
    )
    accounts_df = client.fetch_accounts()
    balances_df = pd.DataFrame()
    if not accounts_df.empty:
        accounts_df = normalize_open_banking_accounts(accounts_df)
        load_dataframe(engine, accounts_df, RAW_SCHEMA, "open_banking_accounts")
        write_schema(ctx.storage, ctx.settings.s3_prefix, f"{RAW_SCHEMA}.open_banking_accounts", accounts_df)
        write_raw_snapshot(ctx, "open_banking_accounts", accounts_df)
        for account_id in accounts_df.get("account_id", []).tolist():
            balances = client.fetch_balances(account_id)
            balances_df = pd.concat([balances_df, normalize_open_banking_balances(balances, account_id)], ignore_index=True)
        if not balances_df.empty:
            load_dataframe(engine, balances_df, RAW_SCHEMA, "open_banking_balances")
            write_schema(ctx.storage, ctx.settings.s3_prefix, f"{RAW_SCHEMA}.open_banking_balances", balances_df)
            write_raw_snapshot(ctx, "open_banking_balances", balances_df)
    return accounts_df, balances_df


def ingest_financials(ctx: PipelineContext, engine) -> pd.DataFrame:
    if not ctx.settings.finstat_urls:
        return pd.DataFrame()
    keys = fetch_financial_statements(
        ctx.settings.finstat_urls,
        storage=ctx.storage,
        key_prefix=ctx.settings.s3_prefix,
        rate_limit_sec=ctx.settings.finstat_rate_limit_sec,
    )
    df = pd.DataFrame(
        {
            "url": ctx.settings.finstat_urls,
            "s3_key": keys,
            "ingested_at": datetime.utcnow().isoformat() + "Z",
        }
    )
    load_dataframe(engine, df, RAW_SCHEMA, "financial_statements")
    write_schema(ctx.storage, ctx.settings.s3_prefix, f"{RAW_SCHEMA}.financial_statements", df)
    return df


def ingest_news(ctx: PipelineContext, engine) -> pd.DataFrame:
    df = fetch_news(
        api_base_url=ctx.settings.news_api_base_url,
        api_key=ctx.settings.news_api_key,
        query=ctx.settings.news_query,
        language=ctx.settings.news_language,
    )
    if df.empty:
        return df
    load_dataframe(engine, df, RAW_SCHEMA, "news")
    write_schema(ctx.storage, ctx.settings.s3_prefix, f"{RAW_SCHEMA}.news", df)
    ctx.checkpoint.set("news", datetime.utcnow().isoformat())
    return df


def ingest_security(ctx: PipelineContext, engine) -> Tuple[pd.DataFrame, pd.DataFrame]:
    last = ctx.checkpoint.get("cve")
    cve_df = fetch_cves(ctx.settings.cve_api_base_url, last_cursor=last)
    if not cve_df.empty:
        load_dataframe(engine, cve_df, RAW_SCHEMA, "cves")
        write_schema(ctx.storage, ctx.settings.s3_prefix, f"{RAW_SCHEMA}.cves", cve_df)
        ctx.checkpoint.set("cve", cve_df["last_modified"].max())

    vt_df = fetch_virustotal_iocs(ctx.settings.virustotal_api_base_url, ctx.settings.virustotal_api_key)
    if not vt_df.empty:
        load_dataframe(engine, vt_df, RAW_SCHEMA, "virustotal")
        write_schema(ctx.storage, ctx.settings.s3_prefix, f"{RAW_SCHEMA}.virustotal", vt_df)
        ctx.checkpoint.set("virustotal", datetime.utcnow().isoformat())

    return cve_df, vt_df


def load_bank_dictionary() -> pd.DataFrame:
    return pd.read_csv("data/dictionaries/bank_dictionary.csv", dtype=str)


def normalize_bcb(ctx: PipelineContext, engine, df: pd.DataFrame) -> None:
    if df.empty:
        return
    load_dataframe(engine, df, STAGING_SCHEMA, "bcb_series")
    write_schema(ctx.storage, ctx.settings.s3_prefix, f"{STAGING_SCHEMA}.bcb_series", df)
    write_lineage(
        ctx.storage,
        ctx.settings.s3_prefix,
        LineageRecord(
            name="bcb_series",
            inputs=[f"{RAW_SCHEMA}.bcb_series"],
            outputs=[f"{STAGING_SCHEMA}.bcb_series"],
            transform="type_cast",
        ),
    )


def normalize_open_banking(
    ctx: PipelineContext,
    engine,
    accounts_df: pd.DataFrame,
    balances_df: pd.DataFrame,
    bank_dict: pd.DataFrame,
) -> None:
    if not accounts_df.empty:
        enriched = accounts_df.merge(bank_dict, how="left", left_on="cnpj", right_on="cnpj")
        load_dataframe(engine, enriched, STAGING_SCHEMA, "open_banking_accounts")
        write_schema(ctx.storage, ctx.settings.s3_prefix, f"{STAGING_SCHEMA}.open_banking_accounts", enriched)
        write_lineage(
            ctx.storage,
            ctx.settings.s3_prefix,
            LineageRecord(
                name="open_banking_accounts",
                inputs=[f"{RAW_SCHEMA}.open_banking_accounts", "dictionary.bank"],
                outputs=[f"{STAGING_SCHEMA}.open_banking_accounts"],
                transform="join_cnpj",
            ),
        )
    if not balances_df.empty:
        load_dataframe(engine, balances_df, STAGING_SCHEMA, "open_banking_balances")
        write_schema(ctx.storage, ctx.settings.s3_prefix, f"{STAGING_SCHEMA}.open_banking_balances", balances_df)
        write_lineage(
            ctx.storage,
            ctx.settings.s3_prefix,
            LineageRecord(
                name="open_banking_balances",
                inputs=[f"{RAW_SCHEMA}.open_banking_balances"],
                outputs=[f"{STAGING_SCHEMA}.open_banking_balances"],
                transform="type_cast",
            ),
        )


def normalize_financials(ctx: PipelineContext, engine, df: pd.DataFrame, bank_dict: pd.DataFrame) -> None:
    if df.empty:
        return
    load_dataframe(engine, df, STAGING_SCHEMA, "financial_statements")
    write_schema(ctx.storage, ctx.settings.s3_prefix, f"{STAGING_SCHEMA}.financial_statements", df)
    write_lineage(
        ctx.storage,
        ctx.settings.s3_prefix,
        LineageRecord(
            name="financial_statements",
            inputs=[f"{RAW_SCHEMA}.financial_statements"],
            outputs=[f"{STAGING_SCHEMA}.financial_statements"],
            transform="copy",
        ),
    )


def normalize_news(ctx: PipelineContext, engine, df: pd.DataFrame) -> None:
    if df.empty:
        return
    load_dataframe(engine, df, STAGING_SCHEMA, "news")
    write_schema(ctx.storage, ctx.settings.s3_prefix, f"{STAGING_SCHEMA}.news", df)
    write_lineage(
        ctx.storage,
        ctx.settings.s3_prefix,
        LineageRecord(
            name="news",
            inputs=[f"{RAW_SCHEMA}.news"],
            outputs=[f"{STAGING_SCHEMA}.news"],
            transform="copy",
        ),
    )


def normalize_security(ctx: PipelineContext, engine, cve_df: pd.DataFrame, vt_df: pd.DataFrame) -> None:
    if not cve_df.empty:
        load_dataframe(engine, cve_df, STAGING_SCHEMA, "cves")
        write_schema(ctx.storage, ctx.settings.s3_prefix, f"{STAGING_SCHEMA}.cves", cve_df)
        write_lineage(
            ctx.storage,
            ctx.settings.s3_prefix,
            LineageRecord(
                name="cves",
                inputs=[f"{RAW_SCHEMA}.cves"],
                outputs=[f"{STAGING_SCHEMA}.cves"],
                transform="copy",
            ),
        )
    if not vt_df.empty:
        load_dataframe(engine, vt_df, STAGING_SCHEMA, "virustotal")
        write_schema(ctx.storage, ctx.settings.s3_prefix, f"{STAGING_SCHEMA}.virustotal", vt_df)
        write_lineage(
            ctx.storage,
            ctx.settings.s3_prefix,
            LineageRecord(
                name="virustotal",
                inputs=[f"{RAW_SCHEMA}.virustotal"],
                outputs=[f"{STAGING_SCHEMA}.virustotal"],
                transform="copy",
            ),
        )


def curated_bcb(ctx: PipelineContext, engine) -> None:
    df = safe_read_table(engine, STAGING_SCHEMA, "bcb_series")
    if df.empty:
        return
    load_dataframe(engine, df, CURATED_SCHEMA, "macro_series", if_exists="replace")
    write_schema(ctx.storage, ctx.settings.s3_prefix, f"{CURATED_SCHEMA}.macro_series", df)
    write_lineage(
        ctx.storage,
        ctx.settings.s3_prefix,
        LineageRecord(
            name="macro_series",
            inputs=[f"{STAGING_SCHEMA}.bcb_series"],
            outputs=[f"{CURATED_SCHEMA}.macro_series"],
            transform="copy",
        ),
    )


def curated_news(ctx: PipelineContext, engine) -> None:
    df = safe_read_table(engine, STAGING_SCHEMA, "news")
    if df.empty:
        return
    if "publishedAt" in df.columns:
        df["publishedAt"] = pd.to_datetime(df["publishedAt"], errors="coerce")
        df["ref_date"] = df["publishedAt"].dt.date
    else:
        df["ref_date"] = datetime.utcnow().date()
    agg = df.groupby(["ref_date"], as_index=False).agg(
        avg_sentiment=("sentiment_score", "mean"),
        article_count=("sentiment_score", "count"),
    )
    load_dataframe(engine, agg, CURATED_SCHEMA, "news_sentiment_daily", if_exists="replace")
    write_schema(ctx.storage, ctx.settings.s3_prefix, f"{CURATED_SCHEMA}.news_sentiment_daily", agg)
    write_lineage(
        ctx.storage,
        ctx.settings.s3_prefix,
        LineageRecord(
            name="news_sentiment_daily",
            inputs=[f"{STAGING_SCHEMA}.news"],
            outputs=[f"{CURATED_SCHEMA}.news_sentiment_daily"],
            transform="daily_aggregation",
        ),
    )


def curated_security(ctx: PipelineContext, engine) -> None:
    df = safe_read_table(engine, STAGING_SCHEMA, "cves")
    if df.empty:
        return
    df["last_modified"] = pd.to_datetime(df["last_modified"], errors="coerce")
    df["ref_date"] = df["last_modified"].dt.date
    agg = df.groupby(["ref_date"], as_index=False).agg(cve_count=("cve_id", "count"))
    load_dataframe(engine, agg, CURATED_SCHEMA, "security_cve_daily", if_exists="replace")
    write_schema(ctx.storage, ctx.settings.s3_prefix, f"{CURATED_SCHEMA}.security_cve_daily", agg)
    write_lineage(
        ctx.storage,
        ctx.settings.s3_prefix,
        LineageRecord(
            name="security_cve_daily",
            inputs=[f"{STAGING_SCHEMA}.cves"],
            outputs=[f"{CURATED_SCHEMA}.security_cve_daily"],
            transform="daily_aggregation",
        ),
    )


def load_dataframe(engine, df: pd.DataFrame, schema: str, table: str, if_exists: str = "append") -> None:
    if df.empty:
        return
    df.to_sql(table, con=engine, schema=schema, if_exists=if_exists, index=False, method="multi")


def safe_read_table(engine, schema: str, table: str) -> pd.DataFrame:
    try:
        return pd.read_sql_table(table, con=engine, schema=schema)
    except Exception:
        return pd.DataFrame()


def write_raw_snapshot(ctx: PipelineContext, source_name: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    key = f"{ctx.settings.s3_prefix}/snapshots/{source_name}/{now}.json"
    payload = {
        "source": source_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "records": df.to_dict(orient="records"),
    }
    ctx.storage.upload_bytes(key, json.dumps(payload, default=str).encode("utf-8"), "application/json")


def validate_raw_schemas(ctx: PipelineContext, engine) -> None:
    expected_columns = {
        "bcb_series": {"series_id", "ref_date", "value"},
        "open_banking_accounts": {"account_id"},
        "open_banking_balances": {"account_id"},
        "financial_statements": {"url", "s3_key"},
        "news": {"sentiment_score"},
        "cves": {"cve_id", "last_modified"},
    }

    errors = []
    for table, expected in expected_columns.items():
        df = safe_read_table(engine, RAW_SCHEMA, table)
        if df.empty:
            continue
        missing = expected - set(df.columns)
        if missing:
            errors.append(f"{RAW_SCHEMA}.{table} missing columns: {sorted(missing)}")

    if errors:
        raise RuntimeError("Schema validation failed: " + "; ".join(errors))
