"""Model evaluation: compare the AI's predicted stars with the stars customers actually gave.

Customers' star ratings act as free ground-truth labels, so we can measure how reliable
the sentiment model is on this specific business without any manual annotation.
"""

from __future__ import annotations

import pandas as pd

from .analysis import stars_to_sentiment


def evaluate(df: pd.DataFrame) -> dict | None:
    data = df.dropna(subset=["rating"])
    if data.empty:
        return None
    actual = data["rating"].round().astype(int)
    pred = data["pred_stars"].astype(int)
    actual_cls = actual.map(stars_to_sentiment)
    pred_cls = data["sentiment"]

    stars_cm = pd.crosstab(actual, pred, rownames=["Actual stars"], colnames=["Predicted stars"])
    stars_cm = stars_cm.reindex(index=range(1, 6), columns=range(1, 6), fill_value=0)
    order = ["negative", "neutral", "positive"]
    cls_cm = pd.crosstab(actual_cls, pred_cls, rownames=["Actual"], colnames=["Predicted"])
    cls_cm = cls_cm.reindex(index=order, columns=order, fill_value=0)

    # Per-class precision / recall on the 3 sentiment classes
    per_class = {}
    for c in order:
        tp = cls_cm.loc[c, c]
        predicted = cls_cm[c].sum()
        support = cls_cm.loc[c].sum()
        per_class[c] = {
            "precision": round(float(tp / predicted), 3) if predicted else None,
            "recall": round(float(tp / support), 3) if support else None,
            "support": int(support),
        }

    # Baseline: always predicting the most frequent class (how good is "dumb"?)
    baseline = round(float(actual_cls.value_counts(normalize=True).iloc[0]), 3)

    return {
        "n": int(len(data)),
        "accuracy_3_classes": round(float((actual_cls == pred_cls).mean()), 3),
        "baseline_majority_class": baseline,
        "exact_star_accuracy": round(float((actual == pred).mean()), 3),
        "within_one_star": round(float(((actual - pred).abs() <= 1).mean()), 3),
        "mean_absolute_error": round(float((actual - pred).abs().mean()), 2),
        "per_class": per_class,
        "confusion_stars": stars_cm,
        "confusion_classes": cls_cm,
    }


def evaluation_markdown(ev: dict | None) -> str:
    if ev is None:
        return ("No star ratings in this file, so the model cannot be evaluated. "
                "Add a 'rating' column to measure accuracy.")
    pc = ev["per_class"]

    def fmt(v):
        return "n/a" if v is None else f"{v:.0%}"

    rows = "\n".join(
        f"| {c} | {fmt(pc[c]['precision'])} | {fmt(pc[c]['recall'])} | {pc[c]['support']} |"
        for c in ["negative", "neutral", "positive"]
    )
    return f"""**How reliable is the AI on these reviews?** Customers' own star ratings are used as ground truth ({ev['n']} reviews).

| Metric | Value |
|---|---|
| Accuracy (negative / neutral / positive) | **{ev['accuracy_3_classes']:.0%}** |
| Baseline (always predict the most common class) | {ev['baseline_majority_class']:.0%} |
| Exact star match | {ev['exact_star_accuracy']:.0%} |
| Within ±1 star | {ev['within_one_star']:.0%} |
| Mean absolute error | {ev['mean_absolute_error']} stars |

| Class | Precision | Recall | Reviews |
|---|---|---|---|
{rows}

Neutral (3-star) reviews are usually the hardest: customers often write mixed text."""
