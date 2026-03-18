import pandas as pd

from models.preprocess import build_preprocess_pipeline


def test_preprocess_pipeline_handles_numeric_and_categorical():
    df = pd.DataFrame(
        {
            "bank_id": ["001", "033", "001"],
            "capital_ratio": [0.1, 0.12, 0.08],
            "trust_label": [1, 0, 1],
        }
    )

    pipeline, feature_cols = build_preprocess_pipeline(df, target_col="trust_label")
    X = df.drop(columns=["trust_label"])
    pipeline.fit(X)

    transformed = pipeline.transform(X)
    assert transformed.shape[0] == df.shape[0]
    assert "bank_id" in feature_cols
