from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

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

try:
    import torch
except Exception:  # pragma: no cover
    torch = None


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


def export_to_torchscript(
    torch_model_path: str,
    output_dir: str,
    input_dim: int,
) -> Optional[str]:
    if torch is None:
        return None

    model = torch.load(torch_model_path, map_location="cpu")
    model.eval()

    example = torch.randn(1, input_dim)
    scripted = torch.jit.trace(model, example)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts_path = out_dir / "model.torchscript.pt"
    scripted.save(str(ts_path))
    return str(ts_path)


def export_model(
    model_path: str,
    sample_csv: str,
    output_dir: str,
    export_format: str = "onnx",
    torch_input_dim: int = 32,
) -> dict:
    output = {}
    export_format = export_format.lower()

    if export_format in {"onnx", "both"}:
        try:
            output["onnx"] = export_to_onnx(model_path, sample_csv, output_dir)
        except RuntimeError:
            output["onnx"] = None
            output["onnx_status"] = "nao especificado (skl2onnx indisponivel no ambiente)"

    if export_format in {"torchscript", "both"}:
        ts_path = export_to_torchscript(model_path, output_dir, input_dim=torch_input_dim)
        output["torchscript"] = ts_path

    _write_converter_stub(Path(output_dir))
    return output


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
    if len(input_names) == 1:
        vector = [float(features.get(name, 0.0)) for name in feature_names]
        feed[input_names[0]] = np.array([vector], dtype=np.float32)
        return feed

    for name in input_names:
        value = features.get(name)
        if isinstance(value, str):
            feed[name] = np.array([[value]], dtype=object)
        else:
            feed[name] = np.array([[0.0 if value is None else float(value)]], dtype=np.float32)
    return feed


def _score(features: dict):
    outputs = session.run(None, _to_feed_dict(features))
    raw = outputs[1] if len(outputs) > 1 else outputs[0]
    score_prob = float(np.ravel(raw)[-1])
    trust_score = max(0.0, min(100.0, score_prob * 100.0))
    risk_class = "baixo" if trust_score >= 70 else ("medio" if trust_score >= 40 else "alto")
    return score_prob, trust_score, risk_class


@app.get("/score/{institution_id}")
def score_by_id(institution_id: str):
    # Placeholder: production service should load features by institution_id.
    score_prob, trust_score, risk_class = _score({})
    return {
        "institution_id": institution_id,
        "score_prob": score_prob,
        "trust_score": trust_score,
        "risk_class": risk_class,
    }


@app.post("/score/batch")
def score_batch(payload: dict):
    items = payload.get("items", [])
    out = []
    for item in items:
        inst = item.get("institution_id", "unknown")
        features = item.get("features", {})
        score_prob, trust_score, risk_class = _score(features)
        out.append(
            {
                "institution_id": inst,
                "score_prob": score_prob,
                "trust_score": trust_score,
                "risk_class": risk_class,
            }
        )
    return {"results": out}
""".strip(),
        encoding="utf-8",
    )


def _write_converter_stub(output_dir: Path) -> None:
    converter = output_dir / "convert_to_service.py"
    converter.write_text(
        """
from pathlib import Path


def convert_model_artifacts(output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Model artifacts ready for microservice at {out}")


if __name__ == "__main__":
    convert_model_artifacts("models/output")
""".strip(),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True, help="Path to best_model.joblib or torch model")
    parser.add_argument("--sample-csv", required=True, help="Training dataset CSV")
    parser.add_argument("--output-dir", default="models/output")
    parser.add_argument("--format", default="onnx", help="onnx|torchscript|both")
    parser.add_argument("--torch-input-dim", type=int, default=32)
    args = parser.parse_args()

    artifacts = export_model(
        model_path=args.model_path,
        sample_csv=args.sample_csv,
        output_dir=args.output_dir,
        export_format=args.format,
        torch_input_dim=args.torch_input_dim,
    )
    print(json.dumps(artifacts, indent=2))


if __name__ == "__main__":
    main()
