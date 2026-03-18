# Security Policy

## Supported Versions

- `main`: suportada
- `dev`: suportada para testes e homologacao

## Report de Vulnerabilidades

Envie relatorio para o canal interno definido pelo mantenedor (ou GitHub Security Advisory, quando habilitado).

Inclua:
- impacto
- passos de reproducao
- evidencias (logs/screenshot)
- sugestao de mitigacao

## Requisitos Minimos de Seguranca

- Segredos apenas por variaveis de ambiente e secret manager/KMS.
- Criptografia em repouso para bancos e objetos.
- TLS entre componentes externos.
- RBAC e principio do menor privilegio.
- Audit logs de acesso e scoring.
- Agentes em ambiente isolado e com token read-only.

## Escopo de Testes de Seguranca

- SCA/dependency scan
- SAST (bandit)
- Secret leak scan
- Prompt injection tests para integracoes com agentes
- Fuzzing de endpoints de API
