import numpy as np

from models.metrics import classify_risk, compute_binary_metrics, probability_to_trust_score


def test_probability_to_trust_score_range():
    probs = np.array([0.0, 0.5, 1.0])
    scores = probability_to_trust_score(probs)
    assert np.all(scores >= 0)
    assert np.all(scores <= 100)
    assert scores.tolist() == [0.0, 50.0, 100.0]


def test_classify_risk_boundaries():
    assert classify_risk(80) == "baixo"
    assert classify_risk(50) == "medio"
    assert classify_risk(20) == "alto"


def test_compute_binary_metrics_includes_custom_cost():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.4, 0.6, 0.9])
    metrics = compute_binary_metrics(y_true, y_prob, cost_matrix={"fp": 2.0, "fn": 7.0})

    assert "roc_auc" in metrics
    assert "pr_auc" in metrics
    assert "brier" in metrics
    assert "ece" in metrics
    assert "custom_cost" in metrics
    assert metrics["custom_cost"] >= 0
