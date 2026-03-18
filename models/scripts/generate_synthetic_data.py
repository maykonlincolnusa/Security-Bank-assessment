from __future__ import annotations

import argparse

from models.synthetic import generate_synthetic_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic trust-score dataset")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="models/output/synthetic_dataset.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = generate_synthetic_dataset(rows=args.rows, seed=args.seed)
    df.to_csv(args.output, index=False)
    print(f"Saved synthetic dataset to {args.output}")


if __name__ == "__main__":
    main()
