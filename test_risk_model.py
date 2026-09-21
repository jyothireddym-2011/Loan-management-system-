import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from ml.risk_model import RiskClassifier, rule_label, LOW, MEDIUM, HIGH
from ml.risk_model.naive_bayes import GaussianNaiveBayes
from ml.risk_model.training_data import generate_synthetic_examples


def test_rule_label_thresholds():
    assert rule_label(1000, 0) == LOW
    assert rule_label(74_999, 0) == LOW
    assert rule_label(75_000, 0) == MEDIUM
    assert rule_label(160_000, 0) == MEDIUM
    assert rule_label(160_001, 0) == HIGH


def test_rule_label_frequent_updates_never_low():
    # Even a tiny amount becomes at least Medium once revised twice.
    assert rule_label(100, 2) == MEDIUM
    assert rule_label(200_000, 3) == HIGH


def test_naive_bayes_fit_predict_roundtrip():
    X, y = generate_synthetic_examples(n=500, seed=1)
    model = GaussianNaiveBayes(classes=["Low", "Medium", "High"]).fit(X, y)
    label, probs = model.predict((10_000, 0))
    assert label in {"Low", "Medium", "High"}
    assert abs(sum(probs.values()) - 1.0) < 1e-6


def test_naive_bayes_rejects_empty_training_set():
    model = GaussianNaiveBayes(classes=["Low", "Medium", "High"])
    with pytest.raises(ValueError):
        model.fit([], [])


def test_classifier_predict_shape():
    clf = RiskClassifier.train(n_samples=500, seed=2)
    result = clf.predict(dual_amount=50_000, update_frequency=0)
    d = result.to_dict()
    assert set(d.keys()) == {
        "risk", "probabilities", "dual_amount", "update_frequency",
        "frequent_updates_flag", "model_version",
    }
    assert d["risk"] in {"Low", "Medium", "High"}


def test_classifier_safety_net_frequent_updates_never_low():
    clf = RiskClassifier.train(n_samples=800, seed=3)
    # A very small amount but revised many times must never come back Low.
    result = clf.predict(dual_amount=500, update_frequency=5)
    assert result.risk != LOW
    assert result.frequent_updates_flag is True


def test_classifier_save_and_load_roundtrip(tmp_path):
    clf = RiskClassifier.train(n_samples=400, seed=4)
    path = clf.save(str(tmp_path / "model.json"))
    loaded = RiskClassifier.load(path)

    a = clf.predict(120_000, 1).to_dict()
    b = loaded.predict(120_000, 1).to_dict()
    assert a["risk"] == b["risk"]
    assert a["probabilities"] == b["probabilities"]


def test_classifier_load_default_trains_if_no_artifact(tmp_path):
    missing_path = str(tmp_path / "does_not_exist.json")
    clf = RiskClassifier.load_default(artifact_path=missing_path)
    result = clf.predict(30_000, 0)
    assert result.risk in {"Low", "Medium", "High"}
