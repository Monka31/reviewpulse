"""Core analysis: sentiment, themes, statistics and rule-based insights."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from . import config
from .models import ProgressFn, _noop


def stars_to_sentiment(stars: float) -> str:
    if pd.isna(stars):
        return "unknown"
    return "negative" if stars <= 2 else "neutral" if stars == 3 else "positive"


@dataclass
class AnalysisResult:
    business_name: str
    business_type: str
    themes: list[str]
    reviews: pd.DataFrame            # one row per review, enriched with predictions
    stats: dict
    theme_table: pd.DataFrame        # one row per theme
    insights: dict                   # rule-based strengths / pain points
    model_info: str
    summary: str | None = None       # LLM summary (markdown), filled later
    replies: dict = field(default_factory=dict)   # review index -> drafted reply
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    @property
    def has_owner_answers(self) -> bool:
        return bool(self.reviews.attrs.get("has_owner_answers", False))

    @property
    def has_ratings(self) -> bool:
        return bool(self.reviews.attrs.get("has_ratings", False))

    @property
    def has_dates(self) -> bool:
        return bool(self.reviews.attrs.get("has_dates", False))

    def unanswered_negative(self) -> pd.DataFrame:
        """Negative reviews (by predicted sentiment or by a 1-2 star rating) with no owner reply."""
        df = self.reviews
        if not self.has_owner_answers:
            return df.iloc[0:0]
        negative = (df["sentiment"] == "negative") | (df["rating"] <= 2)
        out = df[negative & (df["answered"] == False)]  # noqa: E712 (nullable boolean)
        return out.sort_values("date", ascending=False, na_position="last")


def analyze(df: pd.DataFrame, themes: list[str], backend, business_name: str,
            business_type: str, progress: ProgressFn = _noop) -> AnalysisResult:
    """Run sentiment + theme classification on every review and compute statistics."""
    df = df.copy()
    attrs = dict(df.attrs)
    texts = df["text"].tolist()

    progress(0.02, "Analyzing sentiment")
    sent = backend.sentiment(texts, progress=lambda f, d: progress(0.02 + 0.28 * f, "Analyzing sentiment"))
    df["pred_stars"] = [s for s, _ in sent]
    df["pred_confidence"] = [round(c, 3) for _, c in sent]
    df["sentiment"] = df["pred_stars"].map(stars_to_sentiment)

    progress(0.30, "Detecting themes")
    theme_scores = backend.themes(texts, themes,
                                  progress=lambda f, d: progress(0.30 + 0.60 * f, "Detecting themes"))
    assigned = []
    for scores in theme_scores:
        picked = [t for t in themes if scores.get(t, 0) >= config.THEME_THRESHOLD]
        assigned.append(sorted(picked, key=lambda t: -scores[t]))
    df["themes"] = assigned
    df["main_theme"] = [a[0] if a else "other" for a in assigned]
    for t in themes:
        df[f"score::{t}"] = [round(s.get(t, 0.0), 3) for s in theme_scores]

    df.attrs.update(attrs)
    progress(0.92, "Computing statistics")
    stats = compute_stats(df)
    table = theme_breakdown(df, themes)
    insights = derive_insights(table)
    progress(1.0, "Done")
    return AnalysisResult(business_name=business_name, business_type=business_type, themes=themes,
                          reviews=df, stats=stats, theme_table=table, insights=insights,
                          model_info=backend.describe())


def compute_stats(df: pd.DataFrame) -> dict:
    n = len(df)
    counts = df["sentiment"].value_counts()
    stats = {
        "n_reviews": n,
        "pct_positive": round(float(100 * counts.get("positive", 0) / n), 1),
        "pct_neutral": round(float(100 * counts.get("neutral", 0) / n), 1),
        "pct_negative": round(float(100 * counts.get("negative", 0) / n), 1),
        # Average over every rating in the file (including star-only reviews), i.e. the public score.
        "avg_rating": (df.attrs.get("avg_rating_all") or round(float(df["rating"].mean()), 2))
                      if df.attrs.get("has_ratings") else None,
        "avg_rating_written": round(float(df["rating"].mean()), 2) if df.attrs.get("has_ratings") else None,
        "n_rows_total": df.attrs.get("n_rows_total", n),
        "n_rating_only": df.attrs.get("n_rating_only", 0),
        "owner_answers_all_empty": df.attrs.get("owner_answers_all_empty", False),
        "avg_predicted_stars": round(float(df["pred_stars"].mean()), 2),
        "date_min": df["date"].min() if df.attrs.get("has_dates") else None,
        "date_max": df["date"].max() if df.attrs.get("has_dates") else None,
    }
    if df.attrs.get("has_owner_answers"):
        answered = df["answered"].astype(bool)
        negative = (df["sentiment"] == "negative") | (df["rating"] <= 2)
        stats["reply_rate"] = round(float(100 * answered.mean()), 1)
        stats["reply_rate_negative"] = (round(float(100 * answered[negative].mean()), 1)
                                        if negative.any() else None)
        stats["n_unanswered_negative"] = int((negative & ~answered).sum())
    return stats


def theme_breakdown(df: pd.DataFrame, themes: list[str]) -> pd.DataFrame:
    rows = []
    for theme in themes:
        sub = df[df["themes"].map(lambda ts: theme in ts)]
        n = len(sub)
        pos = int((sub["sentiment"] == "positive").sum())
        neg = int((sub["sentiment"] == "negative").sum())
        neu = n - pos - neg
        rows.append({
            "theme": theme,
            "mentions": n,
            "share_of_reviews_%": round(100 * n / len(df), 1) if len(df) else 0,
            "positive": pos,
            "neutral": neu,
            "negative": neg,
            "negative_%": round(100 * neg / n, 1) if n else 0.0,
            # Net score from -100 (all negative) to +100 (all positive)
            "net_score": round(100 * (pos - neg) / n) if n else 0,
            "avg_rating": round(float(sub["rating"].mean()), 2) if n and sub["rating"].notna().any() else None,
        })
    return pd.DataFrame(rows).sort_values("mentions", ascending=False).reset_index(drop=True)


def derive_insights(table: pd.DataFrame) -> dict:
    """Simple, transparent rules (no LLM) so the dashboard is useful even without generation."""
    enough = table[table["mentions"] >= config.MIN_MENTIONS_FOR_INSIGHT]
    strengths = enough[enough["net_score"] > 0].sort_values(["net_score", "mentions"], ascending=False)
    pains = enough[enough["negative"] > 0].sort_values(["negative", "negative_%"], ascending=False)
    return {
        "strengths": strengths["theme"].head(3).tolist(),
        "pain_points": pains["theme"].head(3).tolist(),
    }


def review_label(row: pd.Series, max_len: int = 90) -> str:
    """Short human-readable label used in dropdowns."""
    date = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "no date"
    stars = f"{int(row['rating'])}★" if pd.notna(row["rating"]) else f"~{int(row['pred_stars'])}★"
    text = row["text"].replace("\n", " ")
    text = text if len(text) <= max_len else text[:max_len - 1] + "…"
    return f"#{row.name} · {date} · {stars} · {text}"
