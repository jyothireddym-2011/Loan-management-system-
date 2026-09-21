"""
evaluate.py
-----------
Evaluates RiskClassifier against a held-out synthetic split and reports
accuracy, a confusion matrix, and per-class precision/recall.

Run:
    python -m ml.risk_model.evaluate

Read the banner before trusting the accuracy number: this model is
currently trained and evaluated on data generated from the SAME business
rule it's meant to approximate, so a high score here means "the model
recovered the rule", not "the model predicts real-world default risk".
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from .classifier import RiskClassifier
from .training_data import CLASSES, generate_synthetic_examples


def _train_test_split(X: List[Tuple[float, int]], y: List[str], test_frac: float = 0.25):
    split_at = int(len(X) * (1 - test_frac))
    return X[:split_at], y[:split_at], X[split_at:], y[split_at:]


def confusion_matrix(y_true: List[str], y_pred: List[str]) -> Dict[str, Dict[str, int]]:
    matrix = {actual: {predicted: 0 for predicted in CLASSES} for actual in CLASSES}
    for actual, predicted in zip(y_true, y_pred):
        matrix[actual][predicted] += 1
    return matrix


def precision_recall(matrix: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, float]]:
    stats = {}
    for c in CLASSES:
        tp = matrix[c][c]
        fp = sum(matrix[other][c] for other in CLASSES if other != c)
        fn = sum(matrix[c][other] for other in CLASSES if other != c)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        stats[c] = {"precision": round(precision, 3), "recall": round(recall, 3)}
    return stats


def run_evaluation(n_samples: int = 4000, seed: int = 7) -> dict:
    X, y = generate_synthetic_examples(n=n_samples, seed=seed)
    X_train, y_train, X_test, y_test = _train_test_split(X, y)

    from .naive_bayes import GaussianNaiveBayes

    model = GaussianNaiveBayes(classes=CLASSES).fit(X_train, y_train)

    y_pred = [model.predict(x)[0] for x in X_test]
    correct = sum(1 for a, p in zip(y_test, y_pred) if a == p)
    accuracy = correct / len(y_test)

    matrix = confusion_matrix(y_test, y_pred)
    stats = precision_recall(matrix)

    return {
        "n_train": len(X_train),
        "n_test": len(X_test),
        "accuracy": round(accuracy, 4),
        "confusion_matrix": matrix,
        "per_class": stats,
    }


def _print_report(report: dict) -> None:
    print("=" * 70)
    print("RISK MODEL EVALUATION")
    print("=" * 70)
    print(
        "NOTE: trained + evaluated on synthetic data generated from the "
        "same rule used to label it. This measures self-consistency, "
        "NOT real-world predictive accuracy. Wire in real historical "
        "outcomes via training_data.load_training_examples() before "
        "trusting this for production risk decisions."
    )
    print("-" * 70)
    print(f"train size: {report['n_train']}   test size: {report['n_test']}")
    print(f"accuracy:   {report['accuracy'] * 100:.2f}%")
    print("-" * 70)
    print("confusion matrix (rows=actual, cols=predicted):")
    header = "        " + "".join(f"{c:>10}" for c in CLASSES)
    print(header)
    for actual in CLASSES:
        row = "".join(f"{report['confusion_matrix'][actual][c]:>10}" for c in CLASSES)
        print(f"{actual:>8}{row}")
    print("-" * 70)
    print("per-class precision / recall:")
    for c in CLASSES:
        p = report["per_class"][c]
        print(f"  {c:>6}: precision={p['precision']:.3f}  recall={p['recall']:.3f}")
    print("=" * 70)


if __name__ == "__main__":
    _print_report(run_evaluation())
