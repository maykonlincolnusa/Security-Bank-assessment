from __future__ import annotations

import json
from pathlib import Path

from models.multimodal import MultimodalConfig, train_multimodal_model
from models.synthetic import generate_synthetic_dataset


def main() -> None:
    out_dir = Path("models/output")
    out_dir.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_dataset(rows=500)
    X = df.drop(columns=["trust_label"])
    y = df["trust_label"]

    model, avg_prob = train_multimodal_model(X, y, MultimodalConfig())

    payload = {
        "status": "ok",
        "avg_predicted_probability": avg_prob,
        "note": "Modelo deep multimodal treinado com fallback de embeddings quando necessario.",
    }

    (out_dir / "deep_training_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
