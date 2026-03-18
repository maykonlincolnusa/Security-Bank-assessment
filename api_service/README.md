# Trust Score Service (FastAPI)

Microservico de scoring com FastAPI + Postgres + Redis para servir Trust Score e explicabilidade.

## Endpoints
- `GET /score/{institution_id}`: Trust Score + explicacao (top features)
- `POST /batch/score`: batch scoring assincrono
- `GET /metrics`: Prometheus metrics
- `POST /oauth/token`: template OAuth2 (nao emite token em producao)

## Stack e seguranca
- FastAPI + Uvicorn
- SQLAlchemy async (Postgres)
- Redis para cache e rate limiting por `client_id`
- OAuth2 bearer (template) + RBAC (`auditor`, `analyst`, `system`)
- TLS enforcement opcional (`ENFORCE_TLS=true`)
- CORS whitelist por `CORS_ORIGINS`
- Validacao estrita de payloads (Pydantic strict)
- Audit logs (who/what/when)

## Seguranca de agentes
- Requests de agentes exigem headers assinados (`X-Agent-Id`, `X-Agent-Signature`, `X-Agent-Skill`, `X-Agent-Vetted=true`).
- Skill blacklist e allowlist com vetting (`AGENT_SKILL_BLACKLIST`, `AGENT_SKILL_ALLOWLIST`).
- O agente deve rodar em ambiente isolado.
- O agente NUNCA deve ter credenciais com permissao de escrita em producao.
- Use apenas token de leitura com escopo minimo.

## Secrets
- Nao hardcode secrets.
- Use variaveis de ambiente e gerenciador/KMS (placeholder: `KMS_SECRETS_URI`).

## Rodar localmente
1. Exporte modelo ONNX do modulo `models`:
```bash
PYTHONPATH=. python models/export_model.py \
  --model-path models/output/best_model.joblib \
  --sample-csv models/output/training_dataset.csv \
  --output-dir models/output
```

2. Suba o servico:
```bash
cd api_service
docker compose up -d --build
```

3. Gere token demo local:
```bash
python api_service/scripts/generate_tokens.py --roles analyst --secret change-me-local
```

## Tool schema / SDK / skill
- Tool schema: `api_service/openclaw/tool_schema.json`
- SDK: `api_service/sdk/client.py`
- Skill OpenClaw: `api_service/openclaw/skill_example.py`

## Testes de integracao
- Arquivo: `api_service/tests/test_integration.py`
- Roda contra modelo ONNX exportado (skip automatico se artefato ausente).
