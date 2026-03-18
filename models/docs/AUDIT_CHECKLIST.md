# Audit Checklist - ML/Etica/Security

## Dados e Compliance

- [ ] Base legal documentada para uso de dados (LGPD/GDPR)
- [ ] Minimizacao de dados aplicada
- [ ] Politica de retencao definida
- [ ] Processo de exclusao de dados definido
- [ ] Fontes privadas sem autorizacao marcadas como **nao especificado**

## Modelagem

- [ ] Validacao temporal aplicada (purged/time-series)
- [ ] Metricas obrigatorias reportadas (ROC-AUC, PR-AUC, Brier, calibracao, custo)
- [ ] Explicabilidade disponivel (SHAP/LIME/contrafactual)
- [ ] Tabela comparativa de modelos atualizada
- [ ] Trade-offs e limites documentados

## Fairness e Robustez

- [ ] Fairness por subgrupo calculada
- [ ] Disparate impact dentro da faixa aceitavel definida
- [ ] Equal opportunity gap revisado
- [ ] Testes adversariais executados
- [ ] OOD monitorado e thresholds definidos

## Operacao e Seguranca

- [ ] Modelo exportado em formato seguro (ONNX/TorchScript)
- [ ] Segredos em vault/KMS (sem hardcode)
- [ ] TLS obrigatorio e CORS restrito no microservico
- [ ] Logs de inferencia e auditoria habilitados
- [ ] CI/CD com testes, scan de vulnerabilidade e canary

## Governanca

- [ ] Revisao humana para decisoes de alto impacto
- [ ] Aprovao de risco/legado pelo comite responsavel
- [ ] Plano de rollback de modelo definido
