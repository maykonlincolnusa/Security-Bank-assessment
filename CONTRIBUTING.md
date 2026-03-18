# Contributing Guide

Obrigado por contribuir com o Trust Bank System.

## Fluxo recomendado

1. Faça fork ou trabalhe em branch de feature a partir de `dev`.
2. Use commits semanticos: `feat:`, `fix:`, `docs:`, `chore:`.
3. Rode validações locais antes do PR:
```bash
make lint
make test
make security-check
```
4. Abra PR para `dev` com descricao tecnica clara e plano de rollback.
5. Mantenha PRs pequenos e focados por dominio (`data_pipeline`, `models`, `api_service`, etc.).

## Padroes

- Nao commitar segredos, tokens ou dados privados.
- Para dados privados, use somente ambientes autorizados e com consentimento valido.
- Prefira testes com mocks para APIs externas.
- Documente variaveis de ambiente novas em `.env.example`.

## Checklist de PR

- [ ] Codigo testado localmente
- [ ] Testes atualizados
- [ ] README/docs atualizados
- [ ] Sem segredos hardcoded
- [ ] Impacto em seguranca avaliado
