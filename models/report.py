from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any, Dict, Optional

import matplotlib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import auc, precision_recall_curve, roc_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt


try:
    import shap
except Exception:  # pragma: no cover
    shap = None


def plot_roc_pr_calibration(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    output_dir: str,
    prefix: str = "holdout",
) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    paths = {}

    # ROC
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)
    plt.figure(figsize=(6, 4))
    plt.plot(fpr, tpr, label=f"AUC={roc_auc:.3f}")
    plt.plot([0, 1], [0, 1], "k--", alpha=0.5)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend(loc="lower right")
    roc_path = out / f"{prefix}_roc.png"
    plt.tight_layout()
    plt.savefig(roc_path, dpi=150)
    plt.close()
    paths["roc"] = str(roc_path)

    # PR
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = auc(recall, precision)
    plt.figure(figsize=(6, 4))
    plt.plot(recall, precision, label=f"AUC={pr_auc:.3f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve")
    plt.legend(loc="lower left")
    pr_path = out / f"{prefix}_pr.png"
    plt.tight_layout()
    plt.savefig(pr_path, dpi=150)
    plt.close()
    paths["pr"] = str(pr_path)

    # Calibration
    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=10)
    plt.figure(figsize=(6, 4))
    plt.plot(mean_pred, frac_pos, marker="o", label="Model")
    plt.plot([0, 1], [0, 1], "k--", label="Perfect")
    plt.xlabel("Mean Predicted Value")
    plt.ylabel("Fraction of Positives")
    plt.title("Reliability Diagram")
    plt.legend(loc="upper left")
    cal_path = out / f"{prefix}_calibration.png"
    plt.tight_layout()
    plt.savefig(cal_path, dpi=150)
    plt.close()
    paths["calibration"] = str(cal_path)

    return paths


def generate_html_report(
    output_dir: str,
    metrics: Dict[str, Dict[str, float]],
    feature_importance: Optional[pd.Series] = None,
    shap_values: Optional[Any] = None,
    examples: Optional[list] = None,
    model_comparison: Optional[pd.DataFrame] = None,
    infra_table: Optional[pd.DataFrame] = None,
    plot_paths: Optional[Dict[str, str]] = None,
    references: Optional[list[str]] = None,
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_path = Path(output_dir) / "report.html"

    metrics_df = pd.DataFrame(metrics).T.reset_index().rename(columns={"index": "model"})

    fi_section = ""
    if feature_importance is not None and not feature_importance.empty:
        fi_df = feature_importance.head(20).reset_index()
        fi_df.columns = ["feature", "importance"]
        fi_section = _df_to_html(fi_df, "Top Feature Importance")

    shap_section = ""
    shap_kpi = compute_shap_kpi(shap_values)
    if shap_kpi is not None:
        shap_section = f"<h2>SHAP KPI</h2><p>mean_abs_shap: {shap_kpi:.6f}</p>"

    examples_section = ""
    if examples:
        rows = "".join(
            f"<tr><td>{idx+1}</td><td>{ex.get('score_prob', 0):.3f}</td><td>{ex.get('trust_score', 0):.1f}</td><td>{ex.get('risk_class', 'na')}</td><td>{ex.get('top_features', ex.get('top_contributions', ''))}</td></tr>"
            for idx, ex in enumerate(examples[:10])
        )
        examples_section = (
            "<h2>Instancias Explicadas</h2>"
            "<table><tr><th>#</th><th>Prob</th><th>Trust Score</th><th>Risco</th><th>Top Features</th></tr>"
            f"{rows}</table>"
        )

    model_section = _df_to_html(model_comparison, "Tabela Comparativa de Modelos") if model_comparison is not None else ""
    infra_section = _df_to_html(infra_table, "Requisitos de Infraestrutura") if infra_table is not None else ""

    plots_section = ""
    if plot_paths:
        imgs = []
        for name, path in plot_paths.items():
            p = Path(path)
            if p.exists():
                imgs.append(f"<h3>{name.upper()}</h3><img src='data:image/png;base64,{_img_b64(p)}' width='520' />")
        plots_section = "<h2>Graficos</h2>" + "".join(imgs)

    refs_section = ""
    if references:
        items = "".join(f"<li>{ref}</li>" for ref in references)
        refs_section = f"<h2>Referencias</h2><ul>{items}</ul>"

    html = f"""
    <html>
      <head>
        <title>Trust Score - Relatorio de Modelagem</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 24px; line-height: 1.45; }}
          table, th, td {{ border: 1px solid #ddd; border-collapse: collapse; padding: 8px; }}
          th {{ background: #f5f5f5; }}
          code {{ background: #f7f7f7; padding: 2px 4px; }}
        </style>
      </head>
      <body>
        <h1>Relatorio Automatico - Trust Score</h1>
        <p>Este material e apoio a decisao. Nao substitui revisao humana/regulatoria.</p>
        {_df_to_html(metrics_df, "Metricas")}
        {model_section}
        {infra_section}
        {plots_section}
        {fi_section}
        {shap_section}
        {examples_section}
        {refs_section}
      </body>
    </html>
    """
    report_path.write_text(html, encoding="utf-8")
    return str(report_path)


def generate_markdown_report(
    output_dir: str,
    metrics_df: pd.DataFrame,
    fairness_df: Optional[pd.DataFrame] = None,
    ood_summary: Optional[dict] = None,
    notes: Optional[list[str]] = None,
) -> str:
    path = Path(output_dir) / "report.md"
    lines = [
        "# Trust Score - Relatorio de Avaliacao",
        "",
        "## Resumo Executivo",
        "Sistema de apoio a decisao para score de confianca bancaria.",
        "",
        "## Metricas",
        _table_text(metrics_df),
        "",
    ]

    if fairness_df is not None and not fairness_df.empty:
        lines += ["## Fairness por Grupo", _table_text(fairness_df), ""]

    if ood_summary:
        lines += ["## OOD", json.dumps(ood_summary, indent=2), ""]

    if notes:
        lines += ["## Notas", *[f"- {n}" for n in notes], ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def compute_shap_values(model, X: pd.DataFrame):
    if shap is None:
        return None
    try:
        explainer = shap.Explainer(model, X)
        return explainer(X)
    except Exception:
        return None


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


def _img_b64(path: Path) -> str:
    raw = path.read_bytes()
    return base64.b64encode(raw).decode("utf-8")


def _df_to_html(df: Optional[pd.DataFrame], title: str) -> str:
    if df is None or df.empty:
        return ""
    return f"<h2>{title}</h2>{df.to_html(index=False, border=0)}"


def _table_text(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)
