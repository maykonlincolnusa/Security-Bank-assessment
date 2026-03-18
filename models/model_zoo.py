from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression


try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover
    LGBMClassifier = None

try:
    from catboost import CatBoostClassifier
except Exception:  # pragma: no cover
    CatBoostClassifier = None

try:
    from pytorch_tabnet.tab_model import TabNetClassifier
except Exception:  # pragma: no cover
    TabNetClassifier = None


@dataclass(frozen=True)
class ModelSpec:
    name: str
    estimator: object
    family: str
    interpretability: str
    hardware_notes: str
    use_case: str


def build_model_specs(seed: int = 42) -> Dict[str, ModelSpec]:
    specs: Dict[str, ModelSpec] = {
        "logistic_regression": ModelSpec(
            name="logistic_regression",
            estimator=LogisticRegression(max_iter=500, random_state=seed),
            family="baseline",
            interpretability="alta",
            hardware_notes="CPU leve",
            use_case="prototipagem rapida e baseline auditavel",
        ),
        "random_forest": ModelSpec(
            name="random_forest",
            estimator=RandomForestClassifier(n_estimators=400, random_state=seed, n_jobs=-1),
            family="baseline",
            interpretability="media",
            hardware_notes="CPU moderado",
            use_case="capturar nao linearidades sem tuning pesado",
        ),
    }

    if XGBClassifier is not None:
        specs["xgboost"] = ModelSpec(
            name="xgboost",
            estimator=XGBClassifier(
                n_estimators=500,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=seed,
                eval_metric="logloss",
            ),
            family="baseline",
            interpretability="media",
            hardware_notes="CPU moderado, GPU opcional",
            use_case="tabular robusto em producao",
        )

    if LGBMClassifier is not None:
        specs["lightgbm"] = ModelSpec(
            name="lightgbm",
            estimator=LGBMClassifier(
                n_estimators=600,
                learning_rate=0.04,
                num_leaves=63,
                random_state=seed,
            ),
            family="advanced",
            interpretability="media",
            hardware_notes="CPU eficiente",
            use_case="datasets grandes e treino rapido",
        )

    if CatBoostClassifier is not None:
        specs["catboost"] = ModelSpec(
            name="catboost",
            estimator=CatBoostClassifier(
                depth=6,
                learning_rate=0.05,
                n_estimators=500,
                random_seed=seed,
                verbose=False,
            ),
            family="advanced",
            interpretability="media",
            hardware_notes="CPU/GPU, bom com categoricas",
            use_case="features categoricas com pouca engenharia",
        )

    if TabNetClassifier is not None:
        specs["tabnet"] = ModelSpec(
            name="tabnet",
            estimator=TabNetClassifier(seed=seed, verbose=0),
            family="advanced",
            interpretability="alta (masking interno)",
            hardware_notes="GPU recomendada",
            use_case="tabular complexo com interpretabilidade embutida",
        )

    return specs


def hardware_cost_reference() -> list[dict]:
    """Approximate infrastructure/cost reference for documentation.

    Costs are indicative and should be replaced by vendor quotes.
    """

    return [
        {
            "workload": "treino_baseline_cpu",
            "suggested_instance": "8 vCPU / 32 GB RAM",
            "gpu": "nao",
            "hourly_cost_usd": 0.60,
            "notes": "xgboost/lightgbm/catboost em escala moderada",
        },
        {
            "workload": "treino_deep_multimodal",
            "suggested_instance": "NVIDIA A100 40GB + 16 vCPU",
            "gpu": "sim",
            "hourly_cost_usd": 3.50,
            "notes": "BERT + TCN/LSTM/TFT (estimativa)",
        },
        {
            "workload": "inferencia_online",
            "suggested_instance": "4 vCPU / 16 GB RAM",
            "gpu": "nao",
            "hourly_cost_usd": 0.25,
            "notes": "API FastAPI com ONNX Runtime",
        },
        {
            "workload": "inferencia_batch_alta",
            "suggested_instance": "16 vCPU / 64 GB RAM",
            "gpu": "opcional",
            "hourly_cost_usd": 1.20,
            "notes": "lotes horarios para dezenas de milhares de instituicoes",
        },
    ]


def tradeoff_matrix() -> list[dict]:
    return [
        {
            "modelo": "Logistic Regression",
            "vantagens": "auditavel, rapido, calibravel",
            "desvantagens": "limite em nao linearidades",
            "quando_usar": "baseline regulatorio",
        },
        {
            "modelo": "Random Forest",
            "vantagens": "robusto a ruido, pouca preparacao",
            "desvantagens": "calibracao pior sem pos-processamento",
            "quando_usar": "features tabulares heterogeneas",
        },
        {
            "modelo": "XGBoost",
            "vantagens": "alto desempenho tabular",
            "desvantagens": "tuning pode ser custoso",
            "quando_usar": "producao tabular com SLA",
        },
        {
            "modelo": "LightGBM",
            "vantagens": "treino muito rapido",
            "desvantagens": "sensivel a hiperparametros",
            "quando_usar": "datasets maiores",
        },
        {
            "modelo": "CatBoost",
            "vantagens": "forte com categoricas",
            "desvantagens": "tempo de treino maior que LightGBM",
            "quando_usar": "muitos campos categoricos",
        },
        {
            "modelo": "TabNet",
            "vantagens": "interpretabilidade interna",
            "desvantagens": "depende de mais dados/hardware",
            "quando_usar": "tabular complexo com GPU",
        },
        {
            "modelo": "Deep Multimodal",
            "vantagens": "combina texto + serie + tabular",
            "desvantagens": "alto custo e maior risco operacional",
            "quando_usar": "grandes volumes multimodais",
        },
    ]


def supports_proba(estimator: object) -> bool:
    return hasattr(estimator, "predict_proba") or hasattr(estimator, "decision_function")


def clone_estimator(estimator: object) -> object:
    try:
        from sklearn.base import clone

        return clone(estimator)
    except Exception:  # pragma: no cover
        return estimator


def maybe_get_spec(specs: Dict[str, ModelSpec], name: str) -> Optional[ModelSpec]:
    return specs.get(name)
