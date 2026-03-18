# Security Testing Checklist (Pentest-Oriented)

## 1) Dependency and Supply Chain
- [ ] SCA: `pip-audit`, `safety`, `npm audit` (se aplicavel).
- [ ] Scan de imagem com Trivy.
- [ ] SBOM gerado e arquivado por release.
- [ ] Verificar assinatura de imagem (Cosign) antes do deploy.

## 2) API Security
- [ ] Testar authn/authz (token ausente, expirado, role invalida).
- [ ] Testar rate limiting por `client_id`.
- [ ] Validar input schema (payload malformado, tipos incorretos).
- [ ] Fuzzing de path/query/body/header.
- [ ] Validar TLS redirect/enforcement.

## 3) Agent Security (OpenClaw / Codex-style)
- [ ] Testes de prompt injection (override de instrucoes, tentativa de exfiltracao).
- [ ] Validar allowlist + blacklist de skills.
- [ ] Validar assinatura HMAC de request de agente.
- [ ] Confirmar bloqueio de skills nao vetted.
- [ ] Confirmar que token do agente e read-only (escopo minimo).

## 4) Data Exfiltration
- [ ] Testar politicas de egress filtering.
- [ ] Validar alertas de anomalia para volume/resposta incomum.
- [ ] Confirmar redacao de logs para dados sensiveis.

## 5) Runtime and Infra
- [ ] Falco rules habilitadas e alertando corretamente.
- [ ] NetworkPolicies aplicadas (deny by default).
- [ ] WAF com regras gerenciadas + rate limiting.

## 6) Unit/Integration Examples
- [ ] Unit tests para detectores de prompt injection.
- [ ] Unit tests para validacao de skill allowlist/blacklist.
- [ ] Integration tests para assinatura de agente e RBAC.
