from __future__ import annotations

import argparse
import json

import joblib
import numpy as np

from models.ood import density_autoencoder_stub, mahalanobis_ood
from models.synthetic import generate_synthetic_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OOD detection check")
    parser.add_argument("--model-path", default="models/output/best_model.joblib")
    parser.add_argument("--output-json", default="models/output/ood_summary.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _ = joblib.load(args.model_path)  # model loaded for flow parity

    df = generate_synthetic_dataset(rows=400, seed=1234)
    X = df.drop(columns=["trust_label"])
    numeric = X.select_dtypes(include=[np.number]).fillna(0.0)

    split = int(len(numeric) * 0.7)
    train_mat = numeric.iloc[:split].to_numpy(dtype=float)
    test_mat = numeric.iloc[split:].to_numpy(dtype=float)

    maha = mahalanobis_ood(train_mat, test_mat)
    ae = density_autoencoder_stub(train_mat, test_mat)

    payload = {
        "mahalanobis": {
            "threshold": float(maha.threshold),
            "ood_rate": float(maha.is_ood.mean()),
        },
        "pca_autoencoder": {
            "threshold": float(ae.threshold),
            "ood_rate": float(ae.is_ood.mean()),
        },
    }

    with open(args.output_json, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
