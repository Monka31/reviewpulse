"""Plotly charts shared by the Gradio app and the static HTML reports."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .analysis import AnalysisResult

COLORS = {"positive": "#2f9e5b", "neutral": "#9aa1a9", "negative": "#d64545", "accent": "#3b5bdb"}
FONT = dict(family="Inter, Segoe UI, Arial, sans-serif", size=13, color="#1f2933")


def _layout(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(title=dict(text=title, x=0, font=dict(size=16)), height=height, font=FONT,
                      margin=dict(l=10, r=10, t=55, b=10), plot_bgcolor="white",
                      paper_bgcolor="white", legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    fig.update_xaxes(showgrid=True, gridcolor="#eef0f3", zeroline=False)
    fig.update_yaxes(showgrid=False)
    return fig


def theme_chart(result: AnalysisResult) -> go.Figure:
    """Horizontal stacked bars: what customers love vs what frustrates them, per theme."""
    t = result.theme_table[result.theme_table["mentions"] > 0].sort_values("mentions")
    fig = go.Figure()
    for key, label in [("negative", "Negative"), ("neutral", "Neutral"), ("positive", "Positive")]:
        fig.add_bar(y=t["theme"], x=t[key], name=label, orientation="h", marker_color=COLORS[key],
                    hovertemplate="%{y}: %{x} " + label.lower() + " reviews<extra></extra>")
    fig.update_layout(barmode="stack")
    _layout(fig, "Themes: what customers talk about, and how they feel", height=max(320, 60 + 45 * len(t)))
    fig.update_xaxes(title="Number of reviews")
    return fig


def rating_chart(result: AnalysisResult) -> go.Figure:
    df = result.reviews
    source = "rating" if result.has_ratings else "pred_stars"
    counts = df[source].round().value_counts().reindex(range(1, 6), fill_value=0)
    colors = [COLORS["negative"]] * 2 + [COLORS["neutral"]] + [COLORS["positive"]] * 2
    fig = go.Figure(go.Bar(x=[f"{i}★" for i in counts.index], y=counts.values, marker_color=colors,
                           hovertemplate="%{x}: %{y} reviews<extra></extra>"))
    title = "Star ratings given by customers" if result.has_ratings else "Predicted star ratings"
    _layout(fig, title, height=320)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#eef0f3", title="Reviews")
    return fig


def trend_chart(result: AnalysisResult) -> go.Figure | None:
    df = result.reviews.dropna(subset=["date"])
    if df.empty or df["date"].dt.to_period("M").nunique() < 2:
        return None
    monthly = (df.assign(month=df["date"].dt.to_period("M").dt.to_timestamp())
                 .groupby("month")
                 .agg(reviews=("text", "size"),
                      negative_share=("sentiment", lambda s: 100 * (s == "negative").mean()))
                 .reset_index())
    fig = go.Figure()
    fig.add_bar(x=monthly["month"], y=monthly["reviews"], name="Reviews per month",
                marker_color="#c9d3f5", yaxis="y")
    fig.add_scatter(x=monthly["month"], y=monthly["negative_share"], name="% negative",
                    mode="lines+markers", line=dict(color=COLORS["negative"], width=2.5), yaxis="y2")
    fig.update_layout(yaxis=dict(title="Reviews"),
                      yaxis2=dict(title="% negative", overlaying="y", side="right", range=[0, 100],
                                  showgrid=False))
    return _layout(fig, "Volume and share of negative reviews over time", height=340)


def confusion_chart(cm: pd.DataFrame, title: str) -> go.Figure:
    z = cm.values
    labels_x = [str(c) for c in cm.columns]
    labels_y = [str(i) for i in cm.index]
    fig = go.Figure(go.Heatmap(z=z, x=labels_x, y=labels_y, colorscale="Blues", showscale=False,
                               text=z, texttemplate="%{text}",
                               hovertemplate="Actual %{y} · Predicted %{x}: %{z}<extra></extra>"))
    _layout(fig, title, height=360)
    fig.update_xaxes(title=cm.columns.name, showgrid=False, side="bottom")
    fig.update_yaxes(title=cm.index.name, autorange="reversed")
    return fig
