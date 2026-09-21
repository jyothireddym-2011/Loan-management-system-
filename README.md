# ml — Risk Scoring Module

Standalone package that classifies a lending record's risk level
(`Low` / `Medium` / `High`) from two features:

1. `dual_amount` — outstanding amount for the borrower (existing + new)
2. `update_frequency` — how many times the amount has been revised

## Why this is a separate module

The original review flagged that the risk model was trained only on
synthetic data generated from the same business rule it's meant to
discover, so it isn't learning anything a plain `if/else` wouldn't already
give you. Splitting it out here does three things:

- Makes that limitation explicit and testable (`ml/tests/test_evaluation.py`
  reports accuracy **against the rule it was trained on**, which is the
  honest way to describe this model's current ceiling).
- Gives the model a seam to swap in real historical lending data later
  (`ml/risk_model/training_data.py`) without touching the backend at all.
- Lets the backend depend on a small, versioned, independently-testable
  interface (`RiskClassifier`) instead of reaching into Flask-service code.

## Usage

```python
from ml.risk_model import RiskClassifier

clf = RiskClassifier.load_default()
result = clf.predict(dual_amount=185000, update_frequency=1)
# {'risk': 'High', 'probabilities': {...}, 'model_version': '1.0.0', ...}
```

## Evaluating the model

```bash
python -m ml.risk_model.evaluate
```

Prints accuracy, a confusion matrix, and per-class precision/recall against
held-out synthetic data — and prints a warning banner making clear this is
self-consistency, not real-world validation, until real historical data is
plugged into `training_data.py`.

## Retraining

```python
from ml.risk_model import RiskClassifier
clf = RiskClassifier.train(seed=42, n_samples=4000)
clf.save("ml/risk_model/artifacts/model_v1.json")
```
