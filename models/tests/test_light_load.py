import time

from sklearn.linear_model import LogisticRegression

from models.preprocess import build_preprocess_pipeline
from models.synthetic import generate_synthetic_dataset


def test_light_load_batch_scoring_runtime():
    df = generate_synthetic_dataset(rows=500)
    X = df.drop(columns=["trust_label"])
    y = df["trust_label"]

    pipe, _ = build_preprocess_pipeline(df, target_col="trust_label")
    pipe.steps.append(("model", LogisticRegression(max_iter=300)))
    pipe.fit(X, y)

    start = time.perf_counter()
    scores = pipe.predict_proba(X)[:, 1]
    elapsed = time.perf_counter() - start

    assert len(scores) == len(df)
    assert elapsed < 2.0
