# Model CI/CD (Reference)

## Pipeline stages

1. Build image / dependencies
2. Unit tests (`pytest models/tests`)
3. Security scans (`bandit`, dependency scan)
4. Train with synthetic/public data in CI smoke mode
5. Export ONNX artifact
6. Push model image/artifacts (placeholder)
7. Canary deploy of scoring service
8. Post-deploy validation (latencia, drift, erro)

## Canary strategy

- 10% trafego inicial
- comparar distribuicao de score com baseline
- rollback automatico se erro/latencia acima de SLO

## Metrics for promotion

- ROC-AUC >= baseline - margem definida
- Brier <= baseline + margem definida
- ECE <= threshold
- Fairness constraints aprovadas

## Security controls

- Secrets via env + secret manager
- TLS mandatory
- CORS whitelist
- WAF e rate limiting na API
- Artifact signing/SBOM (na pipeline global do repo)
