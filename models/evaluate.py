from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from models.fairness import compute_group_fairness
from models.metrics import add_score_columns, compute_binary_metrics
from models.ood import density_autoencoder_stub, mahalanobis_ood
from models.preprocess import prepare_feature_frame
from models.report import generate_markdown_report, plot_roc_pr_calibration
from models.robustness import (
    evaluate_score_stability,
    extreme_stress_frame,
    perturb_tabular_features,
    perturb_text_noise,
)
from models.synthetic import generate_synthetic_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Trust Score model")
    parser.add_argument("--model-path", default="models/output/best_model.joblib")
    parser.add_argument("--dataset-path", default="")
    parser.add_argument("--target-col", default="trust_label")
    parser.add_argument("--date-col", default="ref_date")
    parser.add_argument("--output-dir", default="models/output")
    parser.add_argument("--cost-fp", type=float, default=1.0)
    parser.add_argument("--cost-fn", type=float, default=5.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model = joblib.load(args.model_path)

    if args.dataset_path:
        df = pd.read_csv(args.dataset_path)
    else:
        df = generate_synthetic_dataset(rows=600, seed=123)

    if args.target_col not in df.columns:
        raise ValueError(f"Missing target column: {args.target_col}")

    df = prepare_feature_frame(df, target_col=args.target_col, add_missing_flags=True)

    X = df.drop(columns=[args.target_col])
    X = _align_with_model(model, X)
    y = df[args.target_col].astype(int).to_numpy()

    proba = model.predict_proba(X)[:, 1]
    metrics = compute_binary_metrics(y, proba, cost_matrix={"fp": args.cost_fp, "fn": args.cost_fn})

    scored = df.copy()
    scored["score_prob"] = proba
    scored = add_score_columns(scored, prob_col="score_prob")
    scored.to_csv(out_dir / "evaluation_predictions.csv", index=False)

    plot_paths = plot_roc_pr_calibration(y, proba, str(out_dir), prefix="evaluation")

    # Fairness
    fairness_df = pd.DataFrame()
    group_col = "region" if "region" in scored.columns else None
    fairness_summary = {}
    if group_col:
        fair = compute_group_fairness(scored, args.target_col, "score_prob", group_col)
        fairness_df = fair.by_group
        fairness_df.to_csv(out_dir / "evaluation_fairness.csv", index=False)
        fairness_summary = {
            "disparate_impact": fair.disparate_impact,
            "equal_opportunity_gap": fair.equal_opportunity_gap,
        }

    # OOD
    numeric = X.select_dtypes(include=[np.number]).fillna(0.0)
    split = int(len(numeric) * 0.7)
    train_mat = numeric.iloc[:split].to_numpy(dtype=float)
    cand_mat = numeric.iloc[split:].to_numpy(dtype=float)

    maha = mahalanobis_ood(train_mat, cand_mat)
    ae = density_autoencoder_stub(train_mat, cand_mat)

    ood_summary = {
        "mahalanobis_ood_rate": float(maha.is_ood.mean()),
        "mahalanobis_threshold": float(maha.threshold),
        "pca_autoencoder_ood_rate": float(ae.is_ood.mean()),
        "pca_autoencoder_threshold": float(ae.threshold),
    }

    # Adversarial/stress
    sensitive_cols = [
        "capital_ratio",
        "liquidity_ratio",
        "npl_ratio",
        "deposit_volatility",
        "security_incidents",
    ]
    x_pert = perturb_tabular_features(X, sensitive_cols=sensitive_cols, pct=0.05)
    if "news_text" in x_pert.columns:
        x_pert["news_text"] = perturb_text_noise(x_pert["news_text"])

    stability = evaluate_score_stability(model, X, x_pert)

    x_stress = extreme_stress_frame(X)
    stress_proba = model.predict_proba(x_stress)[:, 1]

    eval_payload = {
        "metrics": metrics,
        "fairness": fairness_summary,
        "ood": ood_summary,
        "robustness": {
            "baseline_mean": stability.baseline_mean,
            "perturbed_mean": stability.perturbed_mean,
            "abs_delta_mean": stability.abs_delta_mean,
            "pct_large_delta": stability.pct_large_delta,
            "stress_mean": float(np.mean(stress_proba)),
        },
        "plots": plot_paths,
    }

    (out_dir / "evaluation_summary.json").write_text(json.dumps(eval_payload, indent=2), encoding="utf-8")

    metrics_df = pd.DataFrame([{"model": "loaded_model", **metrics}])
    md_report = generate_markdown_report(
        str(out_dir),
        metrics_df=metrics_df,
        fairness_df=fairness_df,
        ood_summary=ood_summary,
        notes=[
            "Perturbacao adversarial tabular: +-5% em features sensiveis.",
            "Perturbacao textual: substituicao simples de sinonimos/ruido.",
            "Fontes privadas reais: nao especificado.",
        ],
    )

    print("[evaluate] summary:", out_dir / "evaluation_summary.json")
    print("[evaluate] report:", md_report)


def _align_with_model(model, X: pd.DataFrame) -> pd.DataFrame:
    preprocess = model.named_steps.get("preprocess") if hasattr(model, "named_steps") else None
    expected = getattr(preprocess, "feature_names_in_", None)
    if expected is None:
        return X

    safe = X.copy()
    for col in expected:
        if col not in safe.columns:
            safe[col] = 0.0
    safe = safe[[c for c in expected if c in safe.columns]]
    return safe


if __name__ == "__main__":
    main()
