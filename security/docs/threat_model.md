# Threat Model (STRIDE) - Plataforma Trust Score

## Escopo do sistema
Componentes avaliados:
- Ingestao ETL (Airflow + conectores externos)
- Storage (S3/MinIO + PostgreSQL)
- Treino/registro/export do modelo
- API de scoring (FastAPI)
- Integracao com agentes (OpenClaw/Codex-style)
- Dashboard de visualizacao

Ativos criticos:
- Credenciais e tokens
- Dados ingeridos (publicos e autorizados)
- Artefatos de modelo (joblib/ONNX)
- Explicabilidade e relatorios
- Logs de auditoria

## Suposicoes e limites
- Dados privados so entram com consentimento/autorizacao formal.
- Agentes operam sem credenciais de escrita em producao.
- Este documento cobre ameacas tecnicas; requisitos legais locais devem ser validados por time juridico.

## STRIDE por componente

### 1) Ingestao ETL
- Spoofing:
  - Risco: uso de credenciais ETL comprometidas.
  - Controles: IAM least privilege, MFA, short-lived credentials, secret manager.
- Tampering:
  - Risco: adulteracao de payload durante coleta.
  - Controles: TLS, checksum/hash por arquivo, assinatura de origem quando disponivel.
- Repudiation:
  - Risco: operador negar execucao/alteracao de job.
  - Controles: audit log imutavel, trilha de deploy de DAG, segregacao de duty.
- Information Disclosure:
  - Risco: vazamento de dados em logs/raw.
  - Controles: DLP, mascaramento de campos, criptografia at rest (KMS), retention minima.
- Denial of Service:
  - Risco: exaustao por limites de API externa.
  - Controles: retry com backoff, circuit breaker, rate limiting e cache.
- Elevation of Privilege:
  - Risco: DAG executar codigo fora do escopo.
  - Controles: RBAC Airflow, politica de aprovacao de DAG, imagem assinada.

### 2) Storage (S3/DB)
- Spoofing:
  - Risco: acesso por chave roubada.
  - Controles: IAM role, federated identity, rotacao de segredo, VPC endpoint.
- Tampering:
  - Risco: alteracao de historico/dataset.
  - Controles: bucket versioning, object lock, backups, snapshots assinados.
- Repudiation:
  - Risco: acesso sem rastreabilidade.
  - Controles: CloudTrail/audit DB, retention de logs, correlation id.
- Information Disclosure:
  - Risco: exfiltracao de dados.
  - Controles: DLP, egress filtering, anomaly detection, bloqueio de acesso publico.
- Denial of Service:
  - Risco: saturacao de conexao/IO no banco.
  - Controles: pool tuning, read replica, limites de query, autoscaling app.
- Elevation of Privilege:
  - Risco: role ampla em bucket/schema.
  - Controles: separacao por ambiente, policy minima, revisao periodica de grants.

### 3) Model training / export
- Spoofing:
  - Risco: dataset falso no treino.
  - Controles: validacao de schema, checksum de origem, aprovacao humana de dataset.
- Tampering:
  - Risco: modelo adulterado antes de deploy.
  - Controles: assinatura de artefatos, hash no registry, SBOM e provenance.
- Repudiation:
  - Risco: sem rastreabilidade de experimento.
  - Controles: MLflow lineage, metadata de parametros e dataset.
- Information Disclosure:
  - Risco: leakage de feature sensivel.
  - Controles: minimizacao de features, pseudonimizacao, controles de acesso ao experimento.
- Denial of Service:
  - Risco: treino custoso/exaustao de recursos.
  - Controles: quotas de compute, timeouts, monitoramento de custo.
- Elevation of Privilege:
  - Risco: job de treino com permissao de admin.
  - Controles: service account dedicado, sem acesso de escrita fora do escopo.

### 4) API de scoring
- Spoofing:
  - Risco: bearer token forjado.
  - Controles: JWT com issuer/audience, exp curto, rotacao de chave.
- Tampering:
  - Risco: manipular payload de score.
  - Controles: TLS, validacao estrita de schema, assinaturas para requests de agente.
- Repudiation:
  - Risco: chamada nao atribuivel.
  - Controles: audit logs who/what/when + client_id.
- Information Disclosure:
  - Risco: resposta expor dados internos.
  - Controles: principio de minimo necessario, redacao de campos sensiveis, cache seguro.
- Denial of Service:
  - Risco: burst de requests.
  - Controles: rate limiting por client_id, WAF, HPA e timeout defensivo.
- Elevation of Privilege:
  - Risco: bypass de role.
  - Controles: RBAC estrito, testes negativos por role, policy-as-code.

### 5) Integracao com agentes
- Spoofing:
  - Risco: agente nao autorizado se passando por valido.
  - Controles: allowlist de agent_id, assinatura HMAC, token read-only.
- Tampering:
  - Risco: skill nao vetada alterar comportamento.
  - Controles: vetting formal, allowlist + blacklist de skills, assinatura de skill.
- Repudiation:
  - Risco: sem evidencia de acao do agente.
  - Controles: audit log detalhado com agent_id/skill/signature hash.
- Information Disclosure:
  - Risco: prompt injection para exfiltracao.
  - Controles: DLP, egress filtering, sandbox isolado, detector de anomalia, content filters.
- Denial of Service:
  - Risco: chamadas automatizadas em massa.
  - Controles: rate limiting por client_id e por agent_id, quotas por token.
- Elevation of Privilege:
  - Risco: agente com credencial de escrita em producao.
  - Controles: proibicao de write scope, escopo minimo, ambiente isolado, IAM deny-by-default.

### 6) Dashboard
- Spoofing:
  - Risco: conta falsa para acesso visual.
  - Controles: SSO, MFA, sessao curta.
- Tampering:
  - Risco: dashboard exibir dado adulterado.
  - Controles: fonte assinada, integridade de artefatos e API autenticada.
- Repudiation:
  - Risco: acesso nao auditado.
  - Controles: logs de acesso + trilha de consulta.
- Information Disclosure:
  - Risco: exposicao indevida de score/explicabilidade.
  - Controles: controle por perfil, mascaramento e filtros por tenant.
- Denial of Service:
  - Risco: consultas pesadas indisponibilizam painel.
  - Controles: cache, limites de consulta e paginação.
- Elevation of Privilege:
  - Risco: usuario comum acessar funcoes de auditor.
  - Controles: RBAC no backend + verificação no frontend.

## Tabela de mitigacao prioritaria (cross-cutting)
- Exfiltracao de dados:
  - Controles: DLP, egress filtering, anomaly detection, encryption at rest e in transit.
- Comprometimento de supply chain:
  - Controles: SBOM, assinatura de imagem/modelo, scan de dependencia e imagem.
- Credenciais expostas:
  - Controles: KMS/secret manager, rotacao automatica, nunca hardcode.
- Acesso indevido por agente:
  - Controles: isolamento, token read-only, scope minimo, skill vetting e assinatura.

## Risco residual
Mesmo com controles, risco residual existe para:
- dependencias externas e zero-days,
- falha humana de operacao,
- uso indevido do score fora do contexto previsto.

## Aviso legal e operacional
Este sistema e um **auxilio de decisao**. Qualquer classificacao que possa levar a acao regulatoria deve passar por revisao humana e, quando aplicavel, autorizacao legal. O sistema nao deve ser usado para acessar dados protegidos sem consentimento/autorizacao.
