# ML Architecture and Timeline

## Architecture (Mermaid)

```mermaid
flowchart LR
    A[Fontes publicas/autorizadas] --> B[Feature Store raw/staging/curated]
    B --> C[Feature Engineering: ratios, lags, rolling windows]
    C --> D[Validacao temporal purgada]
    D --> E[Modelos baseline/advanced/deep]
    E --> F[Explicabilidade SHAP LIME + contrafactuais]
    E --> G[Robustez: adversarial, OOD, fairness]
    F --> H[Relatorio automatico HTML/Markdown]
    G --> H
    E --> I[Export ONNX/TorchScript]
    I --> J[API de scoring]
```

## Timeline (Mermaid)

```mermaid
gantt
    title Cronograma de Desenvolvimento ML
    dateFormat  YYYY-MM-DD
    section Dados
    Auditoria de fontes e schema         :done, a1, 2026-03-18, 3d
    Engenharia de features               :done, a2, after a1, 4d
    section Modelagem
    Baselines e advanced                 :active, b1, after a2, 5d
    Deep multimodal e incerteza          :b2, after b1, 6d
    section MLOps
    Optuna + MLflow + DVC                :c1, after b1, 4d
    Export e integracao com API          :c2, after c1, 3d
    section Validacao
    Fairness, OOD e adversarial          :d1, after c2, 4d
    Revisao auditoria/etica              :d2, after d1, 2d
```

## Notas

- Fontes privadas reais: **nao especificado**.
- Treino federado em producao: **nao especificado**.
- BNN completa com VI/MCMC: **nao especificado**.
