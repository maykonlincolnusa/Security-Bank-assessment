from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate drift report with Evidently")
    parser.add_argument("--reference", default="models/output/training_dataset.csv")
    parser.add_argument("--current", default="models/output/evaluation_predictions.csv")
    parser.add_argument("--output", default="models/output/drift_report.html")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset
    except Exception:
        print("Evidently nao instalado; monitoramento de drift nao especificado no ambiente atual.")
        return

    ref = pd.read_csv(args.reference)
    cur = pd.read_csv(args.current)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref, current_data=cur)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(output_path))
    print(f"Drift report saved to {output_path}")


if __name__ == "__main__":
    main()
