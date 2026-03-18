from __future__ import annotations

from models.config import load_settings
from models.synthetic import generate_synthetic_dataset
from models.train_pytorch import TorchConfig, train_torch_grouped


def main():
    settings = load_settings()
    df = generate_synthetic_dataset(rows=600, seed=settings.random_seed)
    X = df.drop(columns=["trust_label"])
    y = df["trust_label"]

    _, avg_prob = train_torch_grouped(X, y, TorchConfig())
    print(f"Deep model trained. Mean predicted probability: {avg_prob:.4f}")


if __name__ == "__main__":
    main()
