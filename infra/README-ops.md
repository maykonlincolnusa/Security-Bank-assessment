# README-ops

Guia de deploy seguro em cloud para o Trust Bank System.

## Infraestrutura (Terraform)

Em `infra/terraform`:
- `modules/vpc`: VPC e subnets privadas/publicas
- `modules/iam`: roles e policies de servico
- `modules/rds`: Postgres com encryption at rest, backup e replica opcional
- `modules/s3`: bucket com versioning, lifecycle e bloqueio de acesso publico
- `modules/eks`: cluster Kubernetes com encryption de secrets

Exemplos adicionais:
- `infra/terraform/examples/waf.tf`
- `infra/terraform/examples/rds-cross-region-replica.tf`
- `infra/terraform/examples/gke-cluster.tf`

## Helm

Charts em `infra/charts`:
- `infra/charts/trust-score`
- `infra/charts/airflow`

Suporte a canary rollout no chart `trust-score`.

## CI/CD

Workflows em `.github/workflows/`:
- `ci.yml`: lint, testes, scans e build
- `cd-simulated.yml`: push/deploy simulados

## Observability e Security

- Prometheus alert rules: `infra/observability/prometheus-alerts.yaml`
- Grafana dashboard: `infra/observability/grafana-dashboard-trust-score.json`
- Loki/Fluent Bit values: `infra/observability/`
- NetworkPolicies: `infra/k8s/networkpolicies.yaml`
- Falco rules: `infra/security/falco-rules.yaml`

## DR

- Backups automaticos no RDS
- Replica cross-region (exemplo Terraform)
- Playbook de rollback definido no pipeline CD

## Checklist pre-producao

- [ ] TLS end-to-end habilitado
- [ ] Secrets em KMS/secret manager
- [ ] RBAC e IAM least privilege
- [ ] NetworkPolicies aplicadas
- [ ] WAF com managed rules e rate limiting
- [ ] SBOM e assinatura de imagem habilitados
- [ ] Restore de backup testado
