import numpy as np

from models.ood import mahalanobis_ood


def test_mahalanobis_ood_flags_outliers():
    rng = np.random.default_rng(42)
    train = rng.normal(0, 1, size=(200, 5))
    test = np.vstack([rng.normal(0, 1, size=(40, 5)), rng.normal(5, 1, size=(5, 5))])

    result = mahalanobis_ood(train, test, q=0.99)
    assert result.score.shape[0] == test.shape[0]
    assert result.is_ood.sum() >= 1
