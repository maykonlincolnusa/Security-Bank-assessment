# Architecture Notes

## Componentes

- `data_pipeline/`: ingestao incremental com Airflow, checkpoints no Postgres e raw no MinIO/S3.
- `models/`: engenharia de atributos, treino, avaliacao, explicabilidade e export ONNX.
- `api_service/`: servico de scoring em FastAPI com OAuth2 template, RBAC, rate limit e cache Redis.
- `security/`: threat model STRIDE, templates de compliance e scripts de testes de seguranca.
- `dashboard/`: visualizacao de Trust Score historico e explicabilidade.
- `infra/`: Terraform, Helm, observability, runtime security e DR.

## Fluxo de dados

1. ETL coleta dados publicos/autorizados.
2. Dados sao versionados em camada `raw`, depois normalizados para `staging` e `curated`.
3. Modelos consomem `curated`, treinam e exportam ONNX.
4. API consome features e artefatos ONNX para gerar score e explicacao.
5. Dashboard e agentes read-only consultam API.

## Controles chave

- Criptografia em repouso com KMS placeholder.
- Rate limiting por `client_id`.
- Audit logs (who/what/when).
- Validacao de assinatura de requests de agentes.
- Isolamento de rede via NetworkPolicies.
