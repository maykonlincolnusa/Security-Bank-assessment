# Privacy and Security Notes

## LGPD/GDPR controls

- Data minimization: coletar apenas campos necessarios para score.
- Purpose limitation: uso restrito a avaliacao de confianca institucional.
- Retention policy: manter dados somente pelo periodo definido em politica interna.
- Right to erasure: processo para excluir registros quando aplicavel.

## Differential Privacy and Federated Learning

- DP-SGD: opcao de treino com ruido diferencial em gradientes (nao especificado nesta implementacao base).
- Federated Learning: recomendado quando dados nao podem sair da instituicao (nao especificado).

## Agent and prompt attack resilience

- Sanitizacao de texto de entrada (`sanitize_agent_text`).
- Deteccao de tokens de prompt injection (`prompt_injection_tokens_detected`).
- Bloqueio e auditoria devem ocorrer na camada de API/gateway.
