# Data Pipeline

Pipeline ETL para ingestao de dados publicos/autorizados que alimentam o Trust Score.

## Fontes

- Banco Central do Brasil (series SGS)
- Open Banking (OAuth2 placeholders)
- Demonstracoes financeiras publicas (scraper minimo com rate limit)
- Noticias e alertas regulatorios (sentimento)
- Incidentes de seguranca (CVE feeds publicos)

## Arquitetura

- Orquestracao: Airflow (`dags/etl_score_dag.py`)
- Checkpoint incremental: Postgres
- Raw storage: MinIO/S3
- Camadas: `raw -> staging -> curated`
- Catalogo: `schema.json` + lineage simples

## Rodar localmente

```bash
cd data_pipeline
docker compose up -d --build
```

## Testes

```bash
pytest -q data_pipeline/tests
```

## Compliance

- Nao armazenar dados sensiveis sem criptografia em repouso.
- Respeitar ToS das APIs.
- Para dados privados, exigir autorizacao e consentimento formal.
