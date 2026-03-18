from __future__ import annotations

import argparse
import json

import joblib

from models.robustness import (
    evaluate_score_stability,
    extreme_stress_frame,
    perturb_tabular_features,
    perturb_text_noise,
)
from models.synthetic import generate_synthetic_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adversarial and stress test for Trust Score model")
    parser.add_argument("--model-path", default="models/output/best_model.joblib")
    parser.add_argument("--output-json", default="models/output/adversarial_stress.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = joblib.load(args.model_path)

    df = generate_synthetic_dataset(rows=300, seed=99)
    X = df.drop(columns=["trust_label"])

    sensitive = ["capital_ratio", "liquidity_ratio", "npl_ratio", "security_incidents", "downtime_minutes"]
    X_perturbed = perturb_tabular_features(X, sensitive_cols=sensitive, pct=0.05)
    if "news_text" in X_perturbed.columns:
        X_perturbed["news_text"] = perturb_text_noise(X_perturbed["news_text"])

    stability = evaluate_score_stability(model, X, X_perturbed)

    X_stress = extreme_stress_frame(X)
    stress_mean = float(model.predict_proba(X_stress)[:, 1].mean())

    payload = {
        "stability": {
            "baseline_mean": stability.baseline_mean,
            "perturbed_mean": stability.perturbed_mean,
            "abs_delta_mean": stability.abs_delta_mean,
            "pct_large_delta": stability.pct_large_delta,
        },
        "stress_mean_score": stress_mean,
    }

    with open(args.output_json, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
