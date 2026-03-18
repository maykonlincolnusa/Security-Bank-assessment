# Validation Checklist

## Local

- [ ] `.env` criado a partir de `.env.example`
- [ ] `make setup` executado sem erros
- [ ] `make lint` executado sem erros
- [ ] `make test` executado sem erros
- [ ] `make security-check` executado sem alertas criticos

## Docker

- [ ] `docker compose build` concluido
- [ ] `docker compose up -d` com todos os servicos em `healthy/running`
- [ ] Airflow acessivel em `http://localhost:8080`
- [ ] API acessivel em `http://localhost:8000/docs`
- [ ] Dashboard acessivel em `http://localhost:8501`
- [ ] MinIO console acessivel em `http://localhost:9001`

## Seguranca

- [ ] Nenhum secret real no repositorio
- [ ] JWT e chaves de agente definidos por ambiente
- [ ] TLS habilitado em ambiente nao-local
- [ ] Tokens de agente com escopo minimo e read-only

## Publicacao

- [ ] Branches `main` e `dev` criadas
- [ ] Tag `v0.1.0` criada
- [ ] Workflows CI/CD ativos no GitHub Actions
- [ ] LICENSE, CONTRIBUTING.md e SECURITY.md revisados
