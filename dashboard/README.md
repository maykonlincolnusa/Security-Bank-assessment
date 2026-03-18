# Dashboard PoC

Streamlit dashboard para demonstracao do Trust Score.

## Funcionalidades
- Serie historica de Trust Score por instituicao.
- Breakdown por dominio (financeiro, regulamentar, seguranca, midia).
- Alertas automaticos com thresholds configuraveis.
- Explicabilidade top 10 features (API quando disponivel; fallback sintetico).

## Execucao
```bash
cd dashboard
docker compose up -d --build
```
Acesse `http://localhost:8501`.

## Dados de demo
- `dashboard/data/demo_trust_scores.csv`
- `dashboard/data/demo_explanations.csv`

## Integracao com API
Defina no `docker-compose.yml`:
- `TRUST_SCORE_URL`
- `TRUST_SCORE_TOKEN`

## Aviso
O dashboard e de apoio analitico. Nao usar como decisor unico para acao regulatoria sem revisao humana e autorizacao legal quando aplicavel.
