from models.synthetic import generate_synthetic_dataset
from models.train_pytorch import split_tabular_embedding_features


def test_split_tabular_embedding_features():
    df = generate_synthetic_dataset(rows=20)
    X = df.drop(columns=["trust_label"])

    tab, emb = split_tabular_embedding_features(X)

    assert tab.shape[0] == emb.shape[0] == 20
    assert emb.shape[1] >= 1
    assert all(not c.startswith("news_emb_") for c in tab.columns)
