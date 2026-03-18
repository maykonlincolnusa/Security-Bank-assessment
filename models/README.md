# Models Module - Trust Score Bancario

Modulo de Machine Learning/Deep Learning para gerar **Trust Score (0-100)** e classe de risco (**baixo, medio, alto**) para instituicoes financeiras.

## Resumo Executivo

Este modulo implementa pipeline completo de treino, avaliacao, explicabilidade e robustez para Trust Score com:
- modelos baseline (Logistic Regression, Random Forest, XGBoost)
- modelos avancados (LightGBM, CatBoost, TabNet - quando disponivel)
- opcao deep multimodal (tabular + texto + sinais temporais)
- validacao temporal purgada
- tuning com Optuna
- tracking com MLflow
- versionamento de artefatos com DVC (stages em `models/dvc.yaml`)

> Aviso: sistema de **apoio a decisao**. Nao substitui revisao humana/regulatoria.

## Objetivo de Output

- `score_prob`: probabilidade de confianca (0-1)
- `trust_score`: score continuo (0-100)
- `risk_class`: `baixo` / `medio` / `alto`

## Fontes e Features

### Fontes previstas
- Banco Central do Brasil (series historicas publicas)
- CVM/balancos publicos (PDF/HTML)
- APIs de noticias (GNews/RSS e similares)
- Feeds publicos de seguranca (NVD CVEs, VirusTotal publico)
- Open Banking com OAuth2 (placeholder)
- Fontes internas: **nao especificado**

### Features principais
- Financeiras: `capital_ratio`, `liquidity_ratio`, `roe`, `npl_ratio`, `npa_to_assets_ratio`
- Estabilidade: `deposit_volatility`, `asset_volatility`, lags e rolling windows
- Regulatorias: `warning_count`, `penalty_count`, `regulatory_risk`
- Externas: `avg_sentiment`, `negative_volume`, `search_spike_index`
- Cyber: `security_incidents`
- Operacionais: `downtime_minutes`, `tx_latency_ms`

### Engenharia temporal
- lags: `*_lag_1`, `*_lag_7`
- janelas moveis: medias/desvios/min/max de 7/30/90/365 dias
- autocorrelacao local (`*_autocorr_30`)

## Estrutura

```text
models/
├── train.py
├── evaluate.py
├── export_model.py
├── features.py
├── preprocess.py
├── metrics.py
├── explainability.py
├── robustness.py
├── ood.py
├── fairness.py
├── multimodal.py
├── model_zoo.py
├── uncertainty.py
├── dvc.yaml
├── .env.example
├── notebooks/
├── scripts/
└── tests/
```

## Pipeline de Treino

1. Construcao de dataset (`models/scripts/build_dataset.py`)
2. Split temporal (`temporal_train_test_split`)
3. Validacao temporal purgada (`PurgedTimeSeriesSplit`)
4. Treino baseline/advanced/deep
5. Tuning opcional com Optuna
6. Metricas obrigatorias + custo customizado
7. SHAP/LIME/contrafactual
8. Relatorio HTML/Markdown automatico
9. Export ONNX/TorchScript

## Metricas obrigatorias

- ROC-AUC
- PR-AUC
- Brier score
- Calibracao (ECE + reliability diagram)
- Custo customizado (`cost_fp`, `cost_fn`)

## Explicabilidade

- SHAP (summary/kpi)
- LIME (instancia local)
- Contrafactual (busca gulosa auditavel)
- Exemplos explicados no relatorio

## Robustez e Seguranca

- Adversarial tabular (+/-5% em features sensiveis)
- Ruido/sinonimos em texto
- Stress test com cenarios extremos
- OOD: Mahalanobis e proxy autoencoder (PCA reconstruction)
- Fairness: disparate impact e equal opportunity por grupo
- Prompt injection checks: `models/robustness.py`

## Execucao

### 1) Instalar dependencias

```bash
python -m pip install -r models/requirements.txt
```

### 2) Treinar

```bash
python -m models.train --output-dir models/output --model-set all --cv-mode purged --enable-optuna --optuna-trials 20
```

### 3) Avaliar (holdout)

```bash
python -m models.evaluate --model-path models/output/best_model.joblib --output-dir models/output
```

### 4) Exportar para producao

```bash
python models/export_model.py --model-path models/output/best_model.joblib --sample-csv models/output/training_dataset.csv --output-dir models/output --format onnx
```

### 5) Drift monitoring (opcional)

```bash
python -m models.scripts.monitor_drift --reference models/output/training_dataset.csv --current models/output/evaluation_predictions.csv
```

## DVC e MLflow

- DVC stages: `models/dvc.yaml`
- MLflow: setar `MLFLOW_TRACKING_URI` em `models/.env.example`

Exemplo DVC:
```bash
dvc repro models/dvc.yaml
```

## Testes

```bash
pytest -q models/tests
```

## Notebooks

- `models/notebooks/01_eda_feature_engineering.ipynb`
- `models/notebooks/02_model_training_explainability.ipynb`

## Compliance, etica e auditoria

- LGPD/GDPR: minimizacao, finalidade, retencao limitada, exclusao quando aplicavel
- Revisao humana obrigatoria para decisoes criticas
- Logs e rastreabilidade de score/explicacoes
- Checklist etico: `models/docs/AUDIT_CHECKLIST.md`

## Referencias

- Arik & Pfister, 2019 (TabNet)
- Lim et al., 2019 (Temporal Fusion Transformer)
- CatBoost docs/paper (Yandex)
- LightGBM docs/paper (Microsoft)
- Kendall & Gal, 2017 (uncertainty)
- Docs oficiais: HuggingFace, PyTorch, scikit-learn, XGBoost, Optuna, SHAP, LIME
- Fontes privadas reais: **nao especificado**
