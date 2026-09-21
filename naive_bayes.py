"""
naive_bayes.py
--------------
Minimal Gaussian Naive Bayes classifier for continuous features, implemented
from scratch (no scikit-learn / numpy dependency). Kept generic — it knows
nothing about risk, Aadhaar, or lending; `classifier.py` is the layer that
gives it domain meaning.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple


class GaussianNaiveBayes:
    """Gaussian Naive Bayes over a fixed, ordered list of class labels."""

    def __init__(self, classes: Sequence[str]):
        self.classes: List[str] = list(classes)
        self.priors: Dict[str, float] = {}
        self.means: Dict[str, List[float]] = {}
        self.variances: Dict[str, List[float]] = {}
        self._fitted = False

    def fit(self, X: Sequence[Sequence[float]], y: Sequence[str]) -> "GaussianNaiveBayes":
        n = len(y)
        if n == 0:
            raise ValueError("Cannot fit a model on zero training examples.")

        by_class: Dict[str, List[Sequence[float]]] = {c: [] for c in self.classes}
        for xi, yi in zip(X, y):
            if yi not in by_class:
                raise ValueError(f"Label {yi!r} not in configured classes {self.classes!r}")
            by_class[yi].append(xi)

        for c in self.classes:
            rows = by_class[c] or [tuple(0.0 for _ in X[0])]
            self.priors[c] = max(len(by_class[c]), 1) / n
            n_features = len(rows[0])
            means, variances = [], []
            for f in range(n_features):
                col = [r[f] for r in rows]
                mean = sum(col) / len(col)
                var = sum((v - mean) ** 2 for v in col) / max(len(col) - 1, 1)
                means.append(mean)
                variances.append(max(var, 1e-6))  # avoid div-by-zero on constant columns
            self.means[c] = means
            self.variances[c] = variances

        self._fitted = True
        return self

    @staticmethod
    def _gaussian_log_prob(x: float, mean: float, var: float) -> float:
        return -0.5 * math.log(2 * math.pi * var) - ((x - mean) ** 2) / (2 * var)

    def predict_proba(self, x: Sequence[float]) -> Dict[str, float]:
        if not self._fitted:
            raise RuntimeError("Model must be fit() before predict_proba().")

        log_scores: Dict[str, float] = {}
        for c in self.classes:
            log_p = math.log(self.priors[c])
            for xi, mean, var in zip(x, self.means[c], self.variances[c]):
                log_p += self._gaussian_log_prob(xi, mean, var)
            log_scores[c] = log_p

        # softmax-normalize the log scores into probabilities
        max_log = max(log_scores.values())
        exps = {c: math.exp(v - max_log) for c, v in log_scores.items()}
        total = sum(exps.values())
        return {c: exps[c] / total for c in self.classes}

    def predict(self, x: Sequence[float]) -> Tuple[str, Dict[str, float]]:
        probs = self.predict_proba(x)
        return max(probs, key=probs.get), probs

    def to_dict(self) -> dict:
        """Serialize fitted parameters (small — no need for pickle)."""
        return {
            "classes": self.classes,
            "priors": self.priors,
            "means": self.means,
            "variances": self.variances,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GaussianNaiveBayes":
        model = cls(data["classes"])
        model.priors = data["priors"]
        model.means = data["means"]
        model.variances = data["variances"]
        model._fitted = True
        return model
