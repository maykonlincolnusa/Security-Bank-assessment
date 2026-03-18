# Models Module - Trust Score

Este modulo treina e avalia modelos para gerar Trust Score de instituicoes financeiras.

## Cobertura de features
- Solidez financeira: `capital_ratio`, `liquidity_ratio`, `roe`, `npl_ratio`, `solvency_ratio`
- Estabilidade: `deposit_volatility`, `asset_volatility`
- Sinais regulatorios: `warning_count`, `penalty_count`, `regulatory_risk`
- Sinais externos: `avg_sentiment`, `negative_volume`, `search_spike_index`, `security_incidents`
- Telemetria operacional: `downtime_minutes`
- Deep option: embeddings de noticias `news_emb_*`

## Pipeline ML
- Preprocessamento: `models/preprocess.py` (imputacao, scaling, one-hot)
- Baselines tabulares: Logistic Regression, Random Forest, XGBoost
- Deep option: `models/train_pytorch.py` (tabular + embeddings)
- Time-series: Prophet e LSTM (com fallback)

## Treino e avaliacao
Executar treino completo:
```
PYTHONPATH=. python models/scripts/train_all.py
```

Saidas em `models/output`:
- `training_dataset.csv`
- `metrics.json` (fold metrics)
- `metrics_summary.json`
- `best_model.joblib`
- `report.html`

Metricas:
- ROC-AUC, PR-AUC, Brier, ECE (calibracao)
- KPI de explicabilidade: mean absolute SHAP (quando disponivel)

## Time-series
```
PYTHONPATH=. python models/scripts/train_timeseries.py
```

## Deep option (PyTorch)
```
PYTHONPATH=. python models/scripts/train_deep.py
```

## Export para producao (ONNX + microservice)
```
PYTHONPATH=. python models/export_model.py \
  --model-path models/output/best_model.joblib \
  --sample-csv models/output/training_dataset.csv \
  --output-dir models/output
```

Arquivos gerados:
- `model.onnx`
- `model_features.json`
- `microservice/app.py`

## Testes
```
pytest -q models/tests
```

## Etica e compliance
- Notebook tecnico: `models/notebooks/trust_score_overview.ipynb`
- Notebook etico/legal: `models/notebooks/ethics_bias.ipynb`

Uso recomendado: sistema de apoio a decisao. Acoes regulatorias exigem revisao humana.
