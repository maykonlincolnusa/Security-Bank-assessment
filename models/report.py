from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


try:
    import shap
except Exception:  # pragma: no cover
    shap = None


def generate_html_report(
    output_dir: str,
    metrics: Dict[str, Dict[str, float]],
    feature_importance: Optional[pd.Series] = None,
    shap_values: Optional[Any] = None,
    examples: Optional[list] = None,
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_path = Path(output_dir) / "report.html"

    metrics_table = "".join(
        f"<tr><td>{name}</td>"
        f"<td>{vals.get('roc_auc', 0):.3f}</td>"
        f"<td>{vals.get('pr_auc', 0):.3f}</td>"
        f"<td>{vals.get('brier', 0):.3f}</td>"
        f"<td>{vals.get('ece', 0):.3f}</td></tr>"
        for name, vals in metrics.items()
    )

    fi_section = ""
    if feature_importance is not None and not feature_importance.empty:
        fi_rows = "".join(
            f"<tr><td>{idx}</td><td>{val:.4f}</td></tr>" for idx, val in feature_importance.head(20).items()
        )
        fi_section = (
            "<h2>Feature Importance</h2>"
            "<table><tr><th>Feature</th><th>Importance</th></tr>"
            f"{fi_rows}</table>"
        )

    shap_section = ""
    shap_kpi = compute_shap_kpi(shap_values)
    if shap_kpi is not None:
        shap_section = f"<h2>SHAP KPI</h2><p>mean_abs_shap: {shap_kpi:.6f}</p>"

    examples_section = ""
    if examples:
        example_rows = "".join(
            f"<li>Score: {ex.get('score', 0):.3f} | Top: {ex.get('top_contributions')}</li>"
            for ex in examples
        )
        examples_section = f"<h2>Example Interpretations</h2><ul>{example_rows}</ul>"

    html = f"""
    <html>
      <head>
        <title>Trust Score Report</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 24px; }}
          table, th, td {{ border: 1px solid #ddd; border-collapse: collapse; padding: 8px; }}
          th {{ background: #f5f5f5; }}
        </style>
      </head>
      <body>
        <h1>Model Report</h1>
        <h2>Cross-Validation Metrics</h2>
        <table>
          <tr><th>Model</th><th>ROC-AUC</th><th>PR-AUC</th><th>Brier</th><th>ECE</th></tr>
          {metrics_table}
        </table>
        {fi_section}
        {shap_section}
        {examples_section}
      </body>
    </html>
    """
    report_path.write_text(html, encoding="utf-8")
    return str(report_path)


def compute_shap_values(model, X: pd.DataFrame):
    if shap is None:
        return None
    explainer = shap.Explainer(model, X)
    return explainer(X)


def compute_shap_kpi(shap_values: Any) -> Optional[float]:
    if shap_values is None:
        return None
    values = getattr(shap_values, "values", None)
    if values is None:
        return None
    return float(np.mean(np.abs(values)))


def save_json_metrics(metrics: Dict[str, Dict[str, float]], output_dir: str) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / "metrics_summary.json"
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return str(path)
