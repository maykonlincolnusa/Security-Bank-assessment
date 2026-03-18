from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import TimeSeriesSplit

from models.explainability import generate_explanations
from models.fairness import compute_group_fairness
from models.interpretation import example_interpretations, feature_importance, get_feature_names
from models.metrics import (
    add_score_columns,
    compute_binary_metrics,
    evaluate_model,
    save_metrics,
)
from models.model_zoo import build_model_specs, hardware_cost_reference, tradeoff_matrix
from models.preprocess import PreprocessConfig, build_preprocess_pipeline, prepare_feature_frame
from models.report import generate_html_report, generate_markdown_report, plot_roc_pr_calibration, save_json_metrics
from models.synthetic import generate_synthetic_dataset
from models.temporal_validation import PurgedTimeSeriesSplit, temporal_train_test_split
from models.tuning import OptunaConfig, optimize_tree_model


try:
    import mlflow
except Exception:  # pragma: no cover
    mlflow = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Trust Score models")
    parser.add_argument("--dataset-path", default="", help="CSV path. Empty = synthetic dataset")
    parser.add_argument("--output-dir", default="models/output", help="Output artifacts directory")
    parser.add_argument("--target-col", default="trust_label")
    parser.add_argument("--date-col", default="ref_date")
    parser.add_argument("--model-set", default="all", help="all|baseline|advanced|<model_name>")
    parser.add_argument("--missing-strategy", default="median", help="median|mean|knn")
    parser.add_argument("--enable-optuna", action="store_true")
    parser.add_argument("--optuna-trials", type=int, default=20)
    parser.add_argument("--cv-mode", default="purged", help="purged|timeseries")
    parser.add_argument("--purge-gap-days", type=int, default=3)
    parser.add_argument("--cost-fp", type=float, default=1.0)
    parser.add_argument("--cost-fn", type=float, default=5.0)
    parser.add_argument("--mlflow-uri", default="")
    parser.add_argument("--random-seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = _load_dataset(args.dataset_path, args.target_col)
    df = prepare_feature_frame(df, target_col=args.target_col, add_missing_flags=True)
    df.to_csv(out_dir / "training_dataset.csv", index=False)

    train_df, holdout_df = temporal_train_test_split(df, date_col=args.date_col, test_size=0.2)
    if holdout_df.empty:
        holdout_df = train_df.tail(max(1, len(train_df) // 5)).copy()

    cost_matrix = {"fp": args.cost_fp, "fn": args.cost_fn, "tp": 0.0, "tn": 0.0}

    model_specs = build_model_specs(seed=args.random_seed)
    selected_specs = _select_specs(model_specs, args.model_set)

    results = []
    trained = {}
    holdout_scores = []

    for model_name, spec in selected_specs.items():
        if model_name == "tabnet":
            # TabNet pipeline depends on dense matrix flow and GPU in most production setups.
            # The full tabnet training workflow is provided as optional/not specified here.
            continue

        print(f"[train] model={model_name}")
        pipeline, _ = build_preprocess_pipeline(
            train_df,
            target_col=args.target_col,
            config=PreprocessConfig(target_col=args.target_col, missing_strategy=args.missing_strategy),
        )

        X_train = train_df.drop(columns=[args.target_col])
        y_train = train_df[args.target_col].astype(int)

        tuned_params = _maybe_tune(
            args,
            model_name,
            pipeline,
            spec.estimator,
            X_train,
            y_train,
        )

        estimator = clone(spec.estimator)
        if tuned_params and hasattr(estimator, "set_params"):
            estimator.set_params(**tuned_params)

        pipeline.steps.append(("model", estimator))

        splitter = _build_splitter(args, X_train)
        result = evaluate_model(
            pipeline,
            X_train,
            y_train,
            seed=args.random_seed,
            splitter=splitter,
            cost_matrix=cost_matrix,
        )
        result.name = model_name

        pipeline.fit(X_train, y_train)

        X_holdout = holdout_df.drop(columns=[args.target_col])
        y_holdout = holdout_df[args.target_col].astype(int).to_numpy()

        start = time.perf_counter()
        proba_holdout = pipeline.predict_proba(X_holdout)[:, 1]
        infer_latency_ms = (time.perf_counter() - start) * 1000 / max(1, len(X_holdout))

        hold_metrics = compute_binary_metrics(y_holdout, proba_holdout, cost_matrix=cost_matrix)
        hold_metrics["latency_ms_per_record"] = float(infer_latency_ms)
        result.metrics.update({f"holdout_{k}": v for k, v in hold_metrics.items()})

        scored = holdout_df[["bank_id", args.date_col]].copy() if "bank_id" in holdout_df.columns else holdout_df[[args.date_col]].copy()
        scored["model"] = model_name
        scored["y_true"] = y_holdout
        scored["score_prob"] = proba_holdout
        scored = add_score_columns(scored, prob_col="score_prob")

        holdout_scores.append(scored)
        results.append(result)
        trained[model_name] = pipeline

    if not results:
        raise RuntimeError("No models were successfully trained")

    metrics_path = save_metrics(results, str(out_dir))
    best_result = max(results, key=lambda r: r.metrics.get("holdout_roc_auc", r.metrics.get("roc_auc", 0.0)))
    best_model = trained[best_result.name]

    best_model_path = out_dir / "best_model.joblib"
    joblib.dump(best_model, best_model_path)

    holdout_df_all = pd.concat(holdout_scores, ignore_index=True)
    holdout_df_all.to_csv(out_dir / "holdout_predictions.csv", index=False)

    model_comparison_df = _build_model_comparison_df(results)
    model_comparison_df.to_csv(out_dir / "model_comparison.csv", index=False)

    # Explanations for best model.
    X_train = train_df.drop(columns=[args.target_col])
    preprocessor = best_model.named_steps["preprocess"]
    feature_names = get_feature_names(preprocessor)
    model_obj = best_model.named_steps["model"]
    fi = feature_importance(model_obj, feature_names)

    best_holdout = holdout_df_all[holdout_df_all["model"] == best_result.name].copy()
    base_holdout = holdout_df.copy()
    base_holdout["score_prob"] = best_holdout["score_prob"].to_numpy()[: len(base_holdout)]
    plot_paths = plot_roc_pr_calibration(
        base_holdout[args.target_col].astype(int).to_numpy(),
        base_holdout["score_prob"].to_numpy(),
        str(out_dir),
        prefix="best_model",
    )

    instance_idx = 0
    bundle = generate_explanations(best_model, X_train, X_train.iloc[instance_idx])
    examples = example_interpretations(best_model, X_train, n=5)

    # Fairness table (if subgroup available).
    fairness_group = "region" if "region" in holdout_df.columns else ("client_profile" if "client_profile" in holdout_df.columns else None)
    fairness_df = pd.DataFrame()
    fairness_summary = {}
    if fairness_group is not None:
        fair_input = holdout_df.copy()
        fair_input["score_prob"] = best_holdout["score_prob"].to_numpy()[: len(fair_input)]
        fair = compute_group_fairness(fair_input, args.target_col, "score_prob", fairness_group)
        fairness_df = fair.by_group
        fairness_summary = {
            "disparate_impact": fair.disparate_impact,
            "equal_opportunity_gap": fair.equal_opportunity_gap,
        }
        fairness_df.to_csv(out_dir / "fairness_by_group.csv", index=False)

    metrics_summary = {r.name: r.metrics for r in results}
    if fairness_summary:
        metrics_summary[best_result.name]["disparate_impact"] = fairness_summary["disparate_impact"]
        metrics_summary[best_result.name]["equal_opportunity_gap"] = fairness_summary["equal_opportunity_gap"]

    save_json_metrics(metrics_summary, str(out_dir))

    html_path = generate_html_report(
        output_dir=str(out_dir),
        metrics=metrics_summary,
        feature_importance=fi,
        shap_values=bundle.shap_values,
        examples=[
            {
                "score_prob": float(best_holdout["score_prob"].iloc[i]),
                "trust_score": float(best_holdout["trust_score"].iloc[i]),
                "risk_class": str(best_holdout["risk_class"].iloc[i]),
                "top_features": str(bundle.shap_summary.head(5).to_dict("records")) if i == 0 else str(examples[i - 1].get("top_contributions", {})),
            }
            for i in range(min(5, len(best_holdout)))
        ],
        model_comparison=model_comparison_df,
        infra_table=pd.DataFrame(hardware_cost_reference()),
        plot_paths=plot_paths,
        references=_reference_list(),
    )

    markdown_path = generate_markdown_report(
        output_dir=str(out_dir),
        metrics_df=model_comparison_df,
        fairness_df=fairness_df,
        ood_summary=None,
        notes=[
            "Fonte privada real: nao especificado",
            "TabNet completo para producao: nao especificado",
            "Modelos bayesianos completos: nao especificado",
        ],
    )

    _save_tables_docs(out_dir, model_comparison_df)
    _log_mlflow(args, metrics_summary, best_model_path, html_path, markdown_path)

    print("[done] metrics:", metrics_path)
    print("[done] best_model:", best_model_path)
    print("[done] report_html:", html_path)
    print("[done] report_md:", markdown_path)


def _load_dataset(dataset_path: str, target_col: str) -> pd.DataFrame:
    if dataset_path:
        df = pd.read_csv(dataset_path)
    else:
        df = generate_synthetic_dataset()

    if target_col not in df.columns:
        if "risk_score" in df.columns:
            threshold = float(pd.to_numeric(df["risk_score"], errors="coerce").median())
            df[target_col] = (pd.to_numeric(df["risk_score"], errors="coerce") < threshold).astype(int)
        else:
            # Fallback not specified: generate pseudo-label from available risk proxies.
            risk_proxy = pd.to_numeric(df.get("npl_ratio", 0), errors="coerce").fillna(0.0)
            threshold = float(risk_proxy.median())
            df[target_col] = (risk_proxy < threshold).astype(int)

    return df


def _select_specs(specs: Dict[str, object], model_set: str) -> Dict[str, object]:
    model_set = (model_set or "all").lower()
    if model_set == "all":
        return specs
    if model_set == "baseline":
        return {k: v for k, v in specs.items() if v.family == "baseline"}
    if model_set == "advanced":
        return {k: v for k, v in specs.items() if v.family == "advanced"}
    return {k: v for k, v in specs.items() if k == model_set}


def _build_splitter(args: argparse.Namespace, X_train: pd.DataFrame):
    if args.cv_mode == "timeseries":
        return TimeSeriesSplit(n_splits=5).split(X_train)
    return PurgedTimeSeriesSplit(n_splits=5, purge_gap=args.purge_gap_days).split(X_train, date_col=args.date_col)


def _maybe_tune(
    args: argparse.Namespace,
    model_name: str,
    pipeline,
    estimator,
    X_train,
    y_train,
) -> Dict[str, float]:
    if not args.enable_optuna:
        return {}

    # Temporal validation for tuning uses last 20% of train as validation.
    split = max(1, int(len(X_train) * 0.8))
    X_tr, X_val = X_train.iloc[:split], X_train.iloc[split:]
    y_tr, y_val = y_train.iloc[:split], y_train.iloc[split:]

    if X_val.empty or y_val.nunique() < 2:
        return {}

    cfg = OptunaConfig(enabled=True, trials=args.optuna_trials)

    def base_builder():
        return clone(pipeline)

    def estimator_builder(params):
        est = clone(estimator)
        if hasattr(est, "set_params"):
            est.set_params(**params)
        return est

    return optimize_tree_model(model_name, base_builder, estimator_builder, X_tr, y_tr, X_val, y_val, cfg)


def _build_model_comparison_df(results: List) -> pd.DataFrame:
    rows = []
    for result in results:
        rows.append(
            {
                "model": result.name,
                "roc_auc": result.metrics.get("holdout_roc_auc", result.metrics.get("roc_auc")),
                "pr_auc": result.metrics.get("holdout_pr_auc", result.metrics.get("pr_auc")),
                "brier": result.metrics.get("holdout_brier", result.metrics.get("brier")),
                "ece": result.metrics.get("holdout_ece", result.metrics.get("ece")),
                "custom_cost": result.metrics.get("holdout_custom_cost", result.metrics.get("custom_cost")),
                "latency_ms_per_record": result.metrics.get("holdout_latency_ms_per_record", np.nan),
            }
        )
    return pd.DataFrame(rows).sort_values("roc_auc", ascending=False).reset_index(drop=True)


def _save_tables_docs(out_dir: Path, comparison_df: pd.DataFrame) -> None:
    tradeoffs = pd.DataFrame(tradeoff_matrix())
    tradeoffs.to_csv(out_dir / "tradeoff_table.csv", index=False)
    pd.DataFrame(hardware_cost_reference()).to_csv(out_dir / "infra_requirements.csv", index=False)

    md = [
        "# Tabelas Comparativas",
        "",
        "## Modelos",
        _table_text(comparison_df),
        "",
        "## Trade-offs",
        _table_text(tradeoffs),
        "",
    ]
    (out_dir / "comparative_tables.md").write_text("\n".join(md), encoding="utf-8")


def _log_mlflow(
    args: argparse.Namespace,
    metrics_summary: Dict[str, Dict[str, float]],
    best_model_path: Path,
    html_path: str,
    markdown_path: str,
) -> None:
    if mlflow is None:
        return

    if args.mlflow_uri:
        mlflow.set_tracking_uri(args.mlflow_uri)

    mlflow.set_experiment("trust-score")
    with mlflow.start_run():
        mlflow.log_params(
            {
                "model_set": args.model_set,
                "missing_strategy": args.missing_strategy,
                "cv_mode": args.cv_mode,
                "purge_gap_days": args.purge_gap_days,
                "cost_fp": args.cost_fp,
                "cost_fn": args.cost_fn,
            }
        )

        for model_name, metrics in metrics_summary.items():
            for metric_name, value in metrics.items():
                if isinstance(value, (float, int)):
                    mlflow.log_metric(f"{model_name}_{metric_name}", float(value))

        mlflow.log_artifact(str(best_model_path))
        mlflow.log_artifact(html_path)
        mlflow.log_artifact(markdown_path)


def _reference_list() -> List[str]:
    return [
        "Arik, S. O., & Pfister, T. (2019). TabNet: Attentive Interpretable Tabular Learning.",
        "Lim, B., et al. (2019). Temporal Fusion Transformers for Interpretable Multi-horizon Forecasting.",
        "Prokhorenkova, L., et al. (2018). CatBoost: unbiased boosting with categorical features.",
        "Ke, G., et al. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree.",
        "Kendall, A., & Gal, Y. (2017). What Uncertainties Do We Need in Bayesian Deep Learning for Computer Vision?",
        "Documentacao oficial: scikit-learn, PyTorch, HuggingFace Transformers, XGBoost, LightGBM, Optuna, SHAP, LIME.",
        "Fonte privada real: nao especificado.",
    ]


def _table_text(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)


if __name__ == "__main__":
    main()
