from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression

from models.config import load_settings
from models.data import load_curated_tables
from models.features import FeatureConfig, build_feature_table
from models.interpretation import example_interpretations, feature_importance, get_feature_names
from models.preprocess import build_preprocess_pipeline
from models.report import compute_shap_kpi, compute_shap_values, generate_html_report, save_json_metrics
from models.synthetic import generate_synthetic_dataset
from models.train_baselines import train_baselines


try:
    import mlflow
except Exception:  # pragma: no cover
    mlflow = None


def main():
    settings = load_settings()
    output_dir = Path(settings.experiment_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tables = load_curated_tables(settings.db_url)
    features = build_feature_table(tables, FeatureConfig())

    if features.empty or "trust_label" not in features.columns:
        df = generate_synthetic_dataset()
    else:
        df = features

    # Persist training dataset artifact for reproducibility/export.
    dataset_path = output_dir / "training_dataset.csv"
    df.to_csv(dataset_path, index=False)

    results, _, best_model_path = train_baselines(
        df,
        target_col="trust_label",
        output_dir=str(output_dir),
        seed=settings.random_seed,
    )

    metrics_summary = {r.name: r.metrics for r in results}
    save_json_metrics(metrics_summary, str(output_dir))

    pipeline, _ = build_preprocess_pipeline(df, target_col="trust_label")
    pipeline.steps.append(("model", LogisticRegression(max_iter=400, random_state=settings.random_seed)))
    X = df.drop(columns=["trust_label"])
    y = df["trust_label"]
    pipeline.fit(X, y)

    preprocessor = pipeline.named_steps["preprocess"]
    feat_names = get_feature_names(preprocessor)
    fi = feature_importance(pipeline.named_steps["model"], feat_names)
    examples = example_interpretations(pipeline, X, n=5)

    X_transformed = preprocessor.transform(X)
    shap_values = compute_shap_values(pipeline.named_steps["model"], pd.DataFrame(X_transformed.toarray() if hasattr(X_transformed, "toarray") else X_transformed))
    shap_kpi = compute_shap_kpi(shap_values)
    if shap_kpi is not None:
        metrics_summary["logistic_regression"]["mean_abs_shap"] = shap_kpi

    generate_html_report(str(output_dir), metrics_summary, feature_importance=fi, shap_values=shap_values, examples=examples)

    if mlflow is not None:
        mlflow.set_experiment("trust-score")
        with mlflow.start_run():
            mlflow.log_params({"seed": settings.random_seed, "rows": len(df)})
            flat_metrics = {}
            for model_name, model_metrics in metrics_summary.items():
                for metric_name, metric_value in model_metrics.items():
                    if isinstance(metric_value, (int, float)):
                        flat_metrics[f"{model_name}_{metric_name}"] = metric_value
            if flat_metrics:
                mlflow.log_metrics(flat_metrics)
            mlflow.log_artifact(str(dataset_path))
            mlflow.log_artifact(best_model_path)
            report_path = output_dir / "report.html"
            if report_path.exists():
                mlflow.log_artifact(str(report_path))


if __name__ == "__main__":
    main()
