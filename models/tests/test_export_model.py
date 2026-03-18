from pathlib import Path

import pytest
from sklearn.linear_model import LogisticRegression

from models.export_model import export_to_onnx
from models.preprocess import build_preprocess_pipeline
from models.synthetic import generate_synthetic_dataset


def test_export_to_onnx_smoke(tmp_path):
    pytest.importorskip("skl2onnx")

    df = generate_synthetic_dataset(rows=80)
    X = df.drop(columns=["trust_label"])
    y = df["trust_label"]

    pipe, _ = build_preprocess_pipeline(df, target_col="trust_label")
    pipe.steps.append(("model", LogisticRegression(max_iter=300)))
    pipe.fit(X, y)

    model_path = tmp_path / "best_model.joblib"
    sample_path = tmp_path / "sample.csv"

    import joblib

    joblib.dump(pipe, model_path)
    df.to_csv(sample_path, index=False)

    onnx_path = export_to_onnx(str(model_path), str(sample_path), str(tmp_path))

    assert Path(onnx_path).exists()
    assert (tmp_path / "model_features.json").exists()
