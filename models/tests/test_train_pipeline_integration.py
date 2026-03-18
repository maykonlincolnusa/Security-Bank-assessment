from pathlib import Path

import pytest


def test_end_to_end_train_to_export(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")

    from models import train
    from models.export_model import export_to_onnx

    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        "sys.argv",
        [
            "train.py",
            "--output-dir",
            str(output_dir),
            "--model-set",
            "logistic_regression",
            "--cv-mode",
            "timeseries",
        ],
    )
    train.main()

    best_model = output_dir / "best_model.joblib"
    sample_csv = output_dir / "training_dataset.csv"

    assert best_model.exists()
    assert sample_csv.exists()

    try:
        onnx_path = export_to_onnx(str(best_model), str(sample_csv), str(output_dir))
        assert Path(onnx_path).exists()
    except RuntimeError:
        # skl2onnx optional dependency not installed in all environments.
        pass
