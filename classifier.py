"""
classifier.py
-------------
Public interface the rest of the world (backend services, notebooks, batch
jobs) is meant to import: `RiskClassifier`. Wraps the pure-math
GaussianNaiveBayes with:

  - domain feature prep (dual_amount, update_frequency)
  - a safety net enforcing the non-negotiable business rule that frequent
    revisions must never be reported as Low risk, even if the learned
    model disagrees at the margin
  - versioning + JSON save/load, so a trained model is a reviewable,
    diffable artifact instead of a black box re-trained on every boot
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

from .naive_bayes import GaussianNaiveBayes
from .training_data import (
    CLASSES,
    FREQUENT_UPDATE_THRESHOLD,
    LOW,
    load_training_examples,
)

MODEL_VERSION = "1.0.0"
_DEFAULT_ARTIFACT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "artifacts", "model_v1.json"
)


@dataclass
class RiskResult:
    risk: str
    probabilities: Dict[str, float]
    dual_amount: float
    update_frequency: int
    frequent_updates_flag: bool
    model_version: str = MODEL_VERSION

    def to_dict(self) -> dict:
        return {
            "risk": self.risk,
            "probabilities": {c: round(p, 4) for c, p in self.probabilities.items()},
            "dual_amount": self.dual_amount,
            "update_frequency": self.update_frequency,
            "frequent_updates_flag": self.frequent_updates_flag,
            "model_version": self.model_version,
        }


@dataclass
class RiskClassifier:
    model: GaussianNaiveBayes
    version: str = MODEL_VERSION
    trained_on_n: int = field(default=0)

    # ------------------------------------------------------------------ train
    @classmethod
    def train(cls, n_samples: int = 1200, seed: int = 42) -> "RiskClassifier":
        X, y = load_training_examples(n=n_samples, seed=seed)
        model = GaussianNaiveBayes(classes=CLASSES).fit(X, y)
        return cls(model=model, trained_on_n=len(y))

    # -------------------------------------------------------------- predict
    def predict(self, dual_amount: float, update_frequency: int = 0) -> RiskResult:
        dual_amount = float(dual_amount or 0)
        update_frequency = int(update_frequency or 0)

        label, probs = self.model.predict((dual_amount, update_frequency))

        frequent_flag = update_frequency >= FREQUENT_UPDATE_THRESHOLD
        # Safety net: a borrower with frequent revisions must never be
        # reported as Low risk, even if the learned model disagrees.
        if frequent_flag and label == LOW:
            label = "Medium"

        return RiskResult(
            risk=label,
            probabilities=probs,
            dual_amount=dual_amount,
            update_frequency=update_frequency,
            frequent_updates_flag=frequent_flag,
            model_version=self.version,
        )

    # ------------------------------------------------------------- persist
    def save(self, path: str = _DEFAULT_ARTIFACT_PATH) -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "version": self.version,
            "trained_on_n": self.trained_on_n,
            "model": self.model.to_dict(),
        }
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        return path

    @classmethod
    def load(cls, path: str = _DEFAULT_ARTIFACT_PATH) -> "RiskClassifier":
        with open(path) as f:
            payload = json.load(f)
        model = GaussianNaiveBayes.from_dict(payload["model"])
        return cls(model=model, version=payload["version"], trained_on_n=payload["trained_on_n"])

    @classmethod
    def load_default(cls, artifact_path: Optional[str] = None) -> "RiskClassifier":
        """
        Loads the saved artifact if one exists; otherwise trains fresh
        in-memory (fast — pure python, ~1200 samples, 2 features) so the
        service works out of the box with no separate training step.
        """
        path = artifact_path or _DEFAULT_ARTIFACT_PATH
        if os.path.exists(path):
            try:
                return cls.load(path)
            except Exception:
                pass  # fall through to fresh training if the artifact is corrupt
        return cls.train()
