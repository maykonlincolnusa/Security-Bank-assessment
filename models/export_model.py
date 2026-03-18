from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


try:
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType, StringTensorType
except Exception:  # pragma: no cover
    convert_sklearn = None
    FloatTensorType = None
    StringTensorType = None


def export_to_onnx(model_path: str, sample_csv: str, output_dir: str) -> str:
    if convert_sklearn is None:
        raise RuntimeError("skl2onnx not installed")

    pipeline = joblib.load(model_path)
    sample = pd.read_csv(sample_csv)
    if "trust_label" in sample.columns:
        sample = sample.drop(columns=["trust_label"])

    initial_types = _build_initial_types(sample)
    onnx_model = convert_sklearn(pipeline, initial_types=initial_types)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    onnx_path = out_dir / "model.onnx"
    onnx_path.write_bytes(onnx_model.SerializeToString())

    feature_path = out_dir / "model_features.json"
    feature_path.write_text(json.dumps(list(sample.columns), indent=2), encoding="utf-8")

    _write_microservice_stub(out_dir)
    return str(onnx_path)


def _build_initial_types(sample: pd.DataFrame):
    initial_types = []
    for col in sample.columns:
        if pd.api.types.is_numeric_dtype(sample[col]):
            initial_types.append((col, FloatTensorType([None, 1])))
        else:
            initial_types.append((col, StringTensorType([None, 1])))
    return initial_types


def _write_microservice_stub(output_dir: Path) -> None:
    service_dir = output_dir / "microservice"
    service_dir.mkdir(parents=True, exist_ok=True)

    app_path = service_dir / "app.py"
    app_path.write_text(
        """
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI

app = FastAPI(title="Trust Score ONNX Microservice")

model_dir = Path(__file__).resolve().parent.parent
session = ort.InferenceSession(str(model_dir / "model.onnx"))
feature_names = json.loads((model_dir / "model_features.json").read_text(encoding="utf-8"))
input_names = [i.name for i in session.get_inputs()]


def _to_feed_dict(features: dict):
    feed = {}
    for name in input_names:
        value = features.get(name)
        if isinstance(value, str):
            feed[name] = np.array([[value]], dtype=object)
        else:
            feed[name] = np.array([[0.0 if value is None else float(value)]], dtype=np.float32)
    return feed


@app.post("/score")
def score(payload: dict):
    features = payload.get("features", {})
    feed = _to_feed_dict(features)
    outputs = session.run(None, feed)
    return {"scores": np.ravel(outputs[1] if len(outputs) > 1 else outputs[0]).tolist()}
""".strip(),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True, help="Path to best_model.joblib")
    parser.add_argument("--sample-csv", required=True, help="Training dataset CSV")
    parser.add_argument("--output-dir", default="models/output")
    args = parser.parse_args()

    path = export_to_onnx(args.model_path, args.sample_csv, args.output_dir)
    print(f"Exported ONNX model to {path}")


if __name__ == "__main__":
    main()
