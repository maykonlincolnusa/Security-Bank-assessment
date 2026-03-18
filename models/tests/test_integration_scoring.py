import numpy as np

from sklearn.linear_model import LogisticRegression

from models.preprocess import build_preprocess_pipeline
from models.synthetic import generate_synthetic_dataset


def test_integration_batch_scoring():
    df = generate_synthetic_dataset(rows=120)
    pipeline, _ = build_preprocess_pipeline(df, target_col="trust_label")
    pipeline.steps.append(("model", LogisticRegression(max_iter=200)))

    X = df.drop(columns=["trust_label"])
    y = df["trust_label"]
    pipeline.fit(X, y)

    scores = pipeline.predict_proba(X)[:, 1]
    assert scores.shape[0] == df.shape[0]
    assert np.all((scores >= 0) & (scores <= 1))
