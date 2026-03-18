from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from etl.config import load_settings
from etl.pipeline import run_ingestion_only, run_transform_only, run_validate_schemas_only


default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


with DAG(
    dag_id="financial_trust_score_etl",
    default_args=default_args,
    description="Daily ETL pipeline for financial institution trust score data",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "finance"],
) as dag:
    ingest_task = PythonOperator(
        task_id="ingest_raw_sources",
        python_callable=lambda: run_ingestion_only(load_settings()),
    )

    validate_schema_task = PythonOperator(
        task_id="validate_raw_schemas",
        python_callable=lambda: run_validate_schemas_only(load_settings()),
    )

    transform_task = PythonOperator(
        task_id="load_staging_and_curated",
        python_callable=lambda: run_transform_only(load_settings()),
    )

    ingest_task >> validate_schema_task >> transform_task
