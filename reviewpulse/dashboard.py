"""HTML dashboard shared by the Gradio app and the published reports.

Everything is plain HTML + CSS with charts drawn as inline SVG, so it renders identically
in Gradio, in a static GitHub Pages report and in a notebook, without JavaScript.

Filters (period, stars, theme) only re-slice the reviews that were already analyzed:
no model runs again, so the dashboard updates instantly.
"""

from __future__ import annotations

import html
import math
import re

import markdown as md
import pandas as pd

from .analysis import AnalysisResult, theme_breakdown
from .evaluation import evaluate

ALL_TIME, LAST_12 = "All time", "Last 12 months"
ALL_STARS = "All ratings"
STAR_FILTERS = {ALL_STARS: (1, 5), "1 to 2 stars": (1, 2), "3 stars": (3, 3), "4 to 5 stars": (4, 5)}
ALL_THEMES = "All themes"

POS, NEU, NEG = "#1F8A70", "#C9CED6", "#E8590C"
ACCENT, ACCENT_DARK, ACCENT_DEEP = "#00A0E0", "#0077B3", "#005A87"
THEME_SHADES = ["#005A87", "#0077B3", "#00A0E0", "#6CC8EE", "#BFE6F7", "#DDE3EA"]

CSS = """
.rp{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;color:#101828;font-size:15px;line-height:1.5}
.rp *{box-sizing:border-box}
.rp h1,.rp h2,.rp h3{font-family:"Plus Jakarta Sans",Inter,sans-serif;margin:0;color:#101828}
.rp h1{font-size:28px;font-weight:800;letter-spacing:-.4px;margin:2px 0 4px}
.rp h2{font-size:18px;font-weight:700}.rp h3{font-size:16px;font-weight:700}
.rp p{margin:0}.rp .muted{color:#5B6474}.rp .small{font-size:12px}
.rp .eyebrow{font-size:12px;font-weight:700;color:#0077B3;text-transform:uppercase;letter-spacing:.5px}
.rp.stack,.rp .stack{display:flex;flex-direction:column;gap:20px}
.rp .card{background:#fff;border:1px solid #E4E7EC;border-radius:16px;padding:20px 22px}
.rp .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.rp .kpi{background:#fff;border:1px solid #E4E7EC;border-radius:14px;padding:16px 18px}
.rp .kpi .v{font-family:"Plus Jakarta Sans",Inter,sans-serif;font-size:28px;font-weight:800;margin:6px 0 2px}
.rp .kpi .v small{font-size:15px;color:#5B6474;font-weight:600}
.rp .kpi.alert{background:#FFF7F2;border-color:#F8D3BF}.rp .kpi.alert .l,.rp .kpi.alert .s{color:#8A3A12}
.rp .kpi.alert .v{color:#9A3412}
.rp .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:20px}
.rp .wide{grid-column:1/-1}
.rp .diag{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:14px}
.rp .diag>div{border-radius:12px;padding:14px 16px}
.rp .diag ul,.rp .diag ol{margin:0;padding-left:18px;font-size:14px;display:flex;flex-direction:column;gap:6px}
.rp .diag .t{font-weight:700;margin-bottom:8px}
.rp .legend{display:flex;flex-direction:column;gap:8px;font-size:13px}
.rp .legend span{display:flex;align-items:center;gap:8px}
.rp .sw{width:10px;height:10px;border-radius:3px;display:inline-block;flex:none}
.rp .donut{display:flex;align-items:center;gap:22px;flex-wrap:wrap;margin-top:14px}
.rp .hbar{display:grid;grid-template-columns:140px minmax(0,1fr) 44px;align-items:center;gap:10px;font-size:13px}
.rp .track{height:12px;background:#F2F4F7;border-radius:6px;overflow:hidden;display:flex}
.rp .rows{display:flex;flex-direction:column;gap:11px;margin-top:14px}
.rp .review{border:1px solid #E4E7EC;border-radius:12px;padding:16px}
.rp .meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:12px;color:#5B6474;margin-bottom:6px}
.rp .stars{color:#E8590C;font-size:14px;letter-spacing:1px}.rp .stars i{color:#D0D5DD;font-style:normal}
.rp .more summary{border:0;background:none;padding:4px 0 0;text-align:left;color:#0077B3;font-size:13px;margin-top:4px}
.rp .tag{background:#F2F4F7;color:#344054;padding:2px 8px;border-radius:6px;font-size:12px}
.rp .pill{font-size:12px;font-weight:700;padding:3px 9px;border-radius:20px}
.rp .reply{background:#F0F9FE;border:1px solid #C6E9F8;border-radius:10px;padding:12px 14px;margin-top:12px;font-size:14px;white-space:pre-line}
.rp .reply b{display:block;font-size:12px;color:#005A87;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;white-space:normal}
.rp details summary{cursor:pointer;font-weight:600;font-size:14px;padding:10px;border:1px dashed #D0D5DD;border-radius:10px;background:#FAFBFC;text-align:center;list-style:none;margin-top:12px}
.rp details summary::-webkit-details-marker{display:none}
.rp .notice{font-size:13px;color:#5B6474;background:#F6F7F9;border-radius:10px;padding:10px 12px}
.rp .filters-on{font-size:13px;color:#005A87;background:#E5F5FC;border-radius:10px;padding:8px 12px}
.rp svg text{font-family:Inter,system-ui,sans-serif}
.rp .rp-table{border-collapse:collapse;width:100%;font-size:13px}
.rp .rp-table th{position:sticky;top:0;background:#F6F7F9;text-align:left;font-weight:600;color:#5B6474;padding:8px 10px;border-bottom:1px solid #E4E7EC;z-index:1}
.rp .rp-table td{padding:8px 10px;border-bottom:1px solid #F0F2F5;vertical-align:top}
.rp .empty{padding:40px 20px;text-align:center;color:#5B6474}
@media (max-width:640px){.rp .hbar{grid-template-columns:100px minmax(0,1fr) 40px}.rp h1{font-size:22px}}
"""

FONTS_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
              '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
              '&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">')


def esc(value) -> str:
    return html.escape(str(value))


# ------------------------------------------------------------------ filters
def period_choices(result: AnalysisResult) -> list[str]:
    years = sorted({int(y) for y in result.reviews["date"].dropna().dt.year}, reverse=True)
    return [ALL_TIME, LAST_12] + [str(y) for y in years] if years else [ALL_TIME]


def theme_choices(result: AnalysisResult) -> list[str]:
    return [ALL_THEMES] + list(result.themes)


def _period_mask(dates: pd.Series, period: str) -> pd.Series:
    if period in (None, ALL_TIME):
        return pd.Series(True, index=dates.index)
    if period == LAST_12:
        ref = dates.max()
        return dates >= ref - pd.DateOffset(months=12) if pd.notna(ref) else pd.Series(True, index=dates.index)
    return dates.dt.year == int(period)


def apply_filters(result: AnalysisResult, period=ALL_TIME, stars=ALL_STARS, theme=ALL_THEMES) -> pd.DataFrame:
    df = result.reviews
    mask = _period_mask(df["date"], period)
    lo, hi = STAR_FILTERS.get(stars or ALL_STARS, (1, 5))
    if (lo, hi) != (1, 5):
        # Star filter uses the customer's stars when present, else the AI's predicted stars.
        stars_col = df["rating"].fillna(df["pred_stars"])
        mask &= stars_col.between(lo, hi)
    if theme and theme != ALL_THEMES:
        mask &= df["themes"].map(lambda ts: theme in ts)
    out = df[mask]
    out.attrs.update(df.attrs)
    return out


def is_filtered(period, stars, theme) -> bool:
    return (period or ALL_TIME) != ALL_TIME or (stars or ALL_STARS) != ALL_STARS or (theme or ALL_THEMES) != ALL_THEMES


# ------------------------------------------------------------------ small charts
def donut_svg(parts: list[tuple[str, float, str]], center_value: str, center_label: str) -> str:
    """parts: (label, value, color). Drawn with stroke-dasharray circles."""
    total = sum(v for _, v, _ in parts) or 1
    r, c = 54, 2 * math.pi * 54
    offset, segs = 0.0, []
    for _, v, color in parts:
        length = c * v / total
        if length > 0:
            segs.append(f'<circle r="{r}" cx="75" cy="75" fill="none" stroke="{color}" stroke-width="22" '
                        f'stroke-dasharray="{length:.2f} {c - length:.2f}" stroke-dashoffset="{-offset:.2f}" '
                        f'transform="rotate(-90 75 75)"></circle>')
        offset += length
    label = ", ".join(f"{name} {v / total:.0%}" for name, v, _ in parts)
    return (f'<svg width="150" height="150" viewBox="0 0 150 150" role="img" aria-label="Donut chart: {esc(label)}">'
            f'<circle r="{r}" cx="75" cy="75" fill="none" stroke="#F2F4F7" stroke-width="22"></circle>{"".join(segs)}'
            f'<text x="75" y="76" text-anchor="middle" font-size="24" font-weight="800" fill="#101828" '
            f'font-family="Plus Jakarta Sans, Inter, sans-serif">{esc(center_value)}</text>'
            f'<text x="75" y="94" text-anchor="middle" font-size="11" fill="#5B6474">{esc(center_label)}</text></svg>')


def legend_html(parts: list[tuple[str, float, str]], fmt=lambda v, t: f"{v:.0f}") -> str:
    total = sum(v for _, v, _ in parts) or 1
    return '<div class="legend">' + "".join(
        f'<span><i class="sw" style="background:{color}"></i>{esc(name)} <b>{fmt(v, total)}</b></span>'
        for name, v, color in parts) + "</div>"


def hbar_rows(rows: list[tuple[str, float, float, str, str]]) -> str:
    """rows: (label, fraction 0-1 of the track, unused, color, value text)."""
    return '<div class="rows">' + "".join(
        f'<div class="hbar"><span>{esc(label)}</span><div class="track"><span style="width:{max(frac, 0) * 100:.1f}%;'
        f'background:{color};border-radius:6px"></span></div><span class="muted" style="text-align:right">{esc(value)}</span></div>'
        for label, frac, _, color, value in rows) + "</div>"


def stacked_rows(table: pd.DataFrame) -> str:
    t = table[table["mentions"] > 0]
    if t.empty:
        return '<p class="notice" style="margin-top:14px">No theme detected in this selection.</p>'
    top = t["mentions"].max()
    out = []
    for r in t.itertuples():
        width = 100 * r.mentions / top
        segs = "".join(
            f'<span style="width:{100 * n / r.mentions:.1f}%;background:{color}"></span>'
            for n, color in [(r.positive, POS), (r.neutral, NEU), (r.negative, NEG)] if n)
        out.append(f'<div class="hbar"><span>{esc(r.theme)}</span><div style="width:{width:.1f}%">'
                   f'<div class="track" style="height:14px;border-radius:7px">{segs}</div></div>'
                   f'<span class="muted" style="text-align:right">{r.mentions}</span></div>')
    return '<div class="rows">' + "".join(out) + "</div>"


def trend_svg(points: pd.DataFrame, unit: str) -> str:
    """points: columns label, avg, neg_pct, n. Line = average stars, bars = % of 1-2 star ratings."""
    n = len(points)
    W, H, x0, x1, y0, y1 = 560, 220, 40, 540, 20, 180
    lo = max(1.0, math.floor((points["avg"].min() - 0.2) * 2) / 2)
    hi = 5.0
    neg_max = max(40.0, points["neg_pct"].max() * 1.25)
    step = (x1 - x0) / n
    xs = [x0 + step * (i + 0.5) for i in range(n)]

    def y_avg(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    parts = [f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="#E4E7EC"></line>']
    ticks = [lo + k * 0.5 for k in range(int((hi - lo) / 0.5) + 1)]
    for t in ticks:
        parts.append(f'<line x1="{x0}" y1="{y_avg(t):.1f}" x2="{x1}" y2="{y_avg(t):.1f}" stroke="#F2F4F7"></line>'
                     f'<text x="{x0 - 6}" y="{y_avg(t) + 4:.1f}" font-size="10" fill="#5B6474" text-anchor="end">{t:.1f}</text>')
    show_labels = n <= 14
    bw = min(28, step * 0.55)
    for x, row in zip(xs, points.itertuples()):
        h = row.neg_pct / neg_max * (y1 - y0)
        parts.append(f'<rect x="{x - bw / 2:.1f}" y="{y1 - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="#F9C5AA"></rect>')
        if show_labels and row.neg_pct > 0:
            parts.append(f'<text x="{x:.1f}" y="{y1 - h - 5:.1f}" font-size="10" fill="#9A3412" text-anchor="middle">{row.neg_pct:.0f}%</text>')
        if show_labels or row.Index % max(1, n // 8) == 0:
            parts.append(f'<text x="{x:.1f}" y="{y1 + 20}" font-size="11" fill="#344054" text-anchor="middle">{esc(row.label)}</text>')
    line = " ".join(f"{x:.1f},{y_avg(v):.1f}" for x, v in zip(xs, points["avg"]))
    parts.append(f'<polyline points="{line}" fill="none" stroke="{ACCENT_DARK}" stroke-width="3" stroke-linejoin="round"></polyline>')
    for x, v in zip(xs, points["avg"]):
        parts.append(f'<circle cx="{x:.1f}" cy="{y_avg(v):.1f}" r="4.5" fill="{ACCENT_DARK}"></circle>')
        if show_labels:
            parts.append(f'<text x="{x:.1f}" y="{y_avg(v) - 9:.1f}" font-size="11" font-weight="700" fill="{ACCENT_DEEP}" text-anchor="middle">{v:.1f}</text>')
    aria = "; ".join(f"{r.label}: {r.avg:.1f} stars, {r.neg_pct:.0f}% negative" for r in points.itertuples())
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-height:280px" role="img" '
            f'aria-label="Average rating and share of 1 to 2 star ratings per {unit}: {esc(aria)}">{"".join(parts)}</svg>')


def matrix_svg(table: pd.DataFrame) -> str:
    """Priority matrix: x = mentions, y = net sentiment (-100..100).

    Dots carry a number and the theme names are listed under the chart, so no text can
    ever overlap, whatever the data. Dots that would sit on top of each other are spread.
    """
    t = table[table["mentions"] > 0].sort_values(["mentions", "net_score"], ascending=False).reset_index(drop=True)
    if t.empty:
        return '<p class="notice">No theme detected in this selection.</p>'
    W, H, pad, R = 520, 300, 30, 13
    x_max = t["mentions"].max()
    x_mid, y_mid = (pad + W - pad) / 2, H / 2
    parts = [
        f'<rect x="{pad}" y="0" width="{x_mid - pad - 2}" height="{y_mid - 2}" fill="#F0F9FE" rx="10"></rect>',
        f'<rect x="{x_mid + 2}" y="0" width="{W - pad - x_mid - 2}" height="{y_mid - 2}" fill="#E9F6F1" rx="10"></rect>',
        f'<rect x="{pad}" y="{y_mid + 2}" width="{x_mid - pad - 2}" height="{y_mid - 2}" fill="#F6F7F9" rx="10"></rect>',
        f'<rect x="{x_mid + 2}" y="{y_mid + 2}" width="{W - pad - x_mid - 2}" height="{y_mid - 2}" fill="#FFF1E9" rx="10"></rect>',
        f'<text x="{pad + 10}" y="20" font-size="12" font-weight="600" fill="#005A87">Niche strengths</text>',
        f'<text x="{W - pad - 10}" y="20" font-size="12" font-weight="600" fill="#17694F" text-anchor="end">Strengths to promote</text>',
        f'<text x="{pad + 10}" y="{H - 10}" font-size="12" font-weight="600" fill="#5B6474">Watch</text>',
        f'<text x="{W - pad - 10}" y="{H - 10}" font-size="13" font-weight="700" fill="#9A3412" text-anchor="end">Fix first</text>',
    ]
    # Dot positions inside a margin that keeps them clear of the quadrant titles.
    placed = []
    for r in t.itertuples():
        x = pad + 2 * R + (W - 2 * pad - 4 * R) * (r.mentions / x_max)
        y = y_mid - (r.net_score / 100) * (y_mid - 2.5 * R - 18)
        # Spread dots that would overlap: try small moves around the ideal position.
        for k in range(40):
            if all((x - px) ** 2 + (y - py) ** 2 >= (2 * R + 3) ** 2 for px, py in placed):
                break
            angle = k * 2.4
            dist = (2 * R + 3) * (1 + k // 6) * 0.6
            x = min(W - pad - R, max(pad + R, x + dist * math.cos(angle)))
            y = min(H - R - 18, max(R + 26, y + dist * math.sin(angle)))
        placed.append((x, y))
    legend = []
    for (x, y), r in zip(placed, t.itertuples()):
        color = POS if r.net_score > 20 else NEG if r.net_score < -20 else "#98A2B3"
        num = r.Index + 1
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R}" fill="{color}" stroke="#fff" stroke-width="2"></circle>'
                     f'<text x="{x:.1f}" y="{y + 4.5:.1f}" font-size="12" font-weight="700" fill="#fff" '
                     f'text-anchor="middle">{num}</text>')
        legend.append(f'<span style="display:flex;align-items:center;gap:8px;min-width:0">'
                      f'<i style="flex:none;width:20px;height:20px;border-radius:50%;background:{color};color:#fff;'
                      f'font-style:normal;font-size:11px;font-weight:700;display:flex;align-items:center;'
                      f'justify-content:center">{num}</i><span>{esc(r.theme)} '
                      f'<span class="muted">· {r.mentions} · net {r.net_score:+d}</span></span></span>')
    aria = "; ".join(f"{r.Index + 1} {r.theme}: {r.mentions} mentions, net {r.net_score:+d}" for r in t.itertuples())
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-height:320px" role="img" '
            f'aria-label="Priority matrix: {esc(aria)}">{"".join(parts)}</svg>'
            '<div class="small muted" style="display:flex;justify-content:space-between;margin-top:6px">'
            '<span>Rarely mentioned</span><span>Often mentioned →</span></div>'
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px 16px;'
            f'font-size:13px;margin-top:12px">{"".join(legend)}</div>'
            '<p class="small muted" style="margin-top:10px">Vertical axis: net sentiment (share of positive minus '
            'negative reviews), positive at the top. In the list: mentions · net score.</p>')


def all_reviews_frame(result: AnalysisResult, period=ALL_TIME, stars=ALL_STARS, theme=ALL_THEMES) -> pd.DataFrame:
    """Every review of the file in one table: written ones (with the AI's reading) and star-only ones."""
    written = apply_filters(result, period, stars, theme)
    rows = [{
        "#": idx,
        "Date": r["date"],
        "Stars": r["rating"],
        "Review": r["text"],
        "AI sentiment": r["sentiment"],
        "Themes": ", ".join(r["themes"]),
        "Owner reply": "" if pd.isna(r["answered"]) else ("Answered" if r["answered"] else "Not answered"),
    } for idx, r in written.iterrows()]
    if theme in (None, ALL_THEMES):   # star-only reviews have no theme
        lo, hi = STAR_FILTERS.get(stars or ALL_STARS, (1, 5))
        extra = pd.DataFrame(result.reviews.attrs.get("rating_only_rows", []), columns=["date", "rating", "answered"])
        if not extra.empty:
            extra["date"] = pd.to_datetime(extra["date"], errors="coerce")
            keep = _period_mask(extra["date"], period) & extra["rating"].between(lo, hi)
            for r in extra[keep].itertuples():
                rows.append({"#": "", "Date": r.date, "Stars": r.rating, "Review": "",
                             "AI sentiment": "", "Themes": "",
                             "Owner reply": "" if r.answered is None or pd.isna(r.answered)
                             else ("Answered" if r.answered else "Not answered")})
    out = pd.DataFrame(rows, columns=["#", "Date", "Stars", "Review", "AI sentiment", "Themes", "Owner reply"])
    return out.sort_values("Date", ascending=False, na_position="last").reset_index(drop=True)


def all_reviews_html(table: pd.DataFrame) -> str:
    if table.empty:
        return '<p class="notice">No review in this selection.</p>'
    sent_color = {"positive": POS, "negative": "#C2410C", "neutral": "#5B6474"}
    body = []
    for r in table.itertuples(index=False):
        stars = "" if pd.isna(r.Stars) else f'{int(r.Stars)}★'
        date = "" if pd.isna(r.Date) else f"{r.Date:%Y-%m-%d}"
        review = (esc(r.Review) if r.Review else '<span class="muted">Star-only rating, no text</span>')
        sent = (f'<span style="color:{sent_color.get(r[4], "#5B6474")};font-weight:600">{esc(r[4])}</span>' if r[4] else "")
        reply = r[6]
        reply_html = (f'<span class="pill" style="background:#E9F6F1;color:#17694F">{reply}</span>' if reply == "Answered" else
                      f'<span class="pill" style="background:#FFEDE3;color:#9A3412">{reply}</span>' if reply else "")
        body.append(f"<tr><td style='white-space:nowrap'>{date}</td><td>{stars}</td>"
                    f"<td style='min-width:260px;white-space:pre-line'>{review}</td><td>{sent}</td>"
                    f"<td class='small'>{esc(r.Themes)}</td><td style='white-space:nowrap'>{reply_html}</td></tr>")
    return ('<div style="max-height:520px;overflow:auto;border:1px solid #E4E7EC;border-radius:12px">'
            '<table class="rp-table"><thead><tr><th>Date</th><th>Stars</th><th>Review</th><th>AI sentiment</th>'
            f'<th>Themes</th><th>Owner reply</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>')


# ------------------------------------------------------------------ sections
def _trend_points(result: AnalysisResult, df: pd.DataFrame, period: str, use_all_ratings: bool):
    if use_all_ratings and result.reviews.attrs.get("all_ratings"):
        data = pd.DataFrame(result.reviews.attrs["all_ratings"], columns=["date", "rating"])
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.dropna(subset=["date"])
        data = data[_period_mask(data["date"], period)]
        source = f"all {len(data)} ratings, star-only reviews included"
    else:
        data = df.dropna(subset=["date"]).assign(rating=lambda d: d["rating"].fillna(d["pred_stars"]))
        source = f"{len(data)} reviews in this selection"
    if data.empty:
        return None, "", source
    span_months = (data["date"].max() - data["date"].min()).days / 30.4
    unit = "year" if span_months > 24 else "month"
    key = data["date"].dt.year.astype(str) if unit == "year" else data["date"].dt.strftime("%Y-%m")
    g = data.groupby(key).agg(avg=("rating", "mean"), n=("rating", "size"),
                              neg_pct=("rating", lambda s: 100 * (s <= 2).mean())).reset_index(names="label")
    hidden = g[g["n"] < 3]
    g = g[g["n"] >= 3].reset_index(drop=True)
    if len(g) < 2:
        return None, unit, source
    note = (f" ({', '.join(hidden['label'])} hidden: fewer than 3 ratings)" if not hidden.empty else "")
    return g, unit, source + note


def _diagnosis_html(summary: str | None) -> str:
    if not summary:
        return '<p class="notice">AI summary not generated for this analysis.</p>'
    sections, current = {}, None
    for line in summary.splitlines():
        s = line.strip()
        if s.startswith("#"):
            low = s.lower()
            current = ("strengths" if "strength" in low or "force" in low else
                       "actions" if "action" in low else
                       "improve" if "improve" in low or "amélior" in low or "amelior" in low else None)
            if current:
                sections[current] = []
        elif current and re.match(r"^([-*•]|\d+[.)])\s+", s):
            sections[current].append(re.sub(r"^([-*•]|\d+[.)])\s+", "", s))
    if len(sections) < 2:
        return f'<div style="margin-top:12px;font-size:14px">{md.markdown(summary)}</div>'

    def items(key, tag):
        lis = "".join(f"<li>{md.markdown(i)[3:-4]}</li>" for i in sections.get(key, [])) or "<li>n/a</li>"
        return f"<{tag}>{lis}</{tag}>"

    return ('<div class="diag">'
            f'<div style="background:#F3FAF7"><p class="t" style="color:#17694F">Strengths</p>{items("strengths", "ul")}</div>'
            f'<div style="background:#FFF7F2"><p class="t" style="color:#9A3412">To improve</p>{items("improve", "ul")}</div>'
            f'<div style="background:#E5F5FC"><p class="t" style="color:#005A87">Priority actions</p>{items("actions", "ol")}</div>'
            '</div>')


def _review_text(text: str, limit: int = 420) -> str:
    """Long reviews are shortened, with the full text one click away."""
    if len(text) <= limit:
        return f'<p style="font-size:14px;white-space:pre-line">{esc(text)}</p>'
    cut = text[:limit].rsplit(" ", 1)[0]
    return (f'<p style="font-size:14px;white-space:pre-line">{esc(cut)}…</p>'
            f'<details class="more"><summary>Read the full review</summary>'
            f'<p style="font-size:14px;white-space:pre-line;margin-top:6px">{esc(text)}</p></details>')


def _review_card(result: AnalysisResult, idx, row, with_reply: bool) -> str:
    stars = int(row["rating"]) if pd.notna(row["rating"]) else int(row["pred_stars"])
    star_txt = "★" * stars + "<i>" + "★" * (5 - stars) + "</i>"
    date = row["date"].strftime("%b %d, %Y") if pd.notna(row["date"]) else "no date"
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in row["themes"])
    reply = result.replies.get(idx) if with_reply else None
    reply_html = (f'<div class="reply"><b>Suggested reply · AI draft, review before posting</b>{esc(reply)}</div>'
                  if reply else "")
    return (f'<article class="review"><div class="meta"><span class="stars" aria-label="{stars} out of 5 stars">'
            f'{star_txt}</span><span>{date}</span><span class="muted">#{idx}</span>{tags}</div>'
            f'{_review_text(row["text"])}{reply_html}</article>')


def render_dashboard(result: AnalysisResult, period=ALL_TIME, stars=ALL_STARS, theme=ALL_THEMES,
                     show_cards: int = 5) -> str:
    df = apply_filters(result, period, stars, theme)
    filtered = is_filtered(period, stars, theme)
    s = result.stats

    # ---- header
    meta = f"{s['n_reviews']} written reviews analyzed"
    if s.get("n_rating_only"):
        meta += f", plus {s['n_rating_only']} star-only ratings"
    if s.get("date_min") is not None and pd.notna(s["date_min"]):
        meta += f" · {s['date_min']:%b %Y} to {s['date_max']:%b %Y}"
    header = (f'<div><p class="eyebrow">{esc(result.business_type)}</p><h1>{esc(result.business_name)}</h1>'
              f'<p class="muted" style="font-size:14px">{esc(meta)}</p></div>')
    chips = []
    for value, default in [(period, ALL_TIME), (stars, ALL_STARS), (theme, ALL_THEMES)]:
        if value and value != default:
            chips.append(esc(value))
    filter_note = (f'<p class="filters-on">Filtered view: {" · ".join(chips)} · {len(df)} written reviews match</p>'
                   if filtered else "")

    if df.empty:
        return (f'<div class="rp stack">{header}{filter_note}<div class="card empty">'
                'No review matches these filters. Try a wider period or another theme.</div></div>')

    # ---- KPIs
    n = len(df)
    neg_mask = (df["sentiment"] == "negative") | (df["rating"] <= 2)
    pos_n = int((df["sentiment"] == "positive").sum())
    neg_n = int((df["sentiment"] == "negative").sum())
    neu_n = n - pos_n - neg_n
    if not filtered and s.get("avg_rating"):
        avg_v, avg_sub = f"{s['avg_rating']:.2f}", f"over {s['n_rows_total']} ratings"
    elif df["rating"].notna().any():
        avg_v, avg_sub = f"{df['rating'].mean():.2f}", f"over {int(df['rating'].notna().sum())} reviews in this view"
    else:
        avg_v, avg_sub = f"~{df['pred_stars'].mean():.1f}", "predicted by the AI (no stars in file)"
    written_sub = (f"average {df['rating'].mean():.2f} / 5 when people write" if df["rating"].notna().any()
                   else "reviews with text")
    kpis = [
        f'<div class="kpi"><p class="muted small l">Average rating</p><p class="v">{avg_v}<small> / 5</small></p><p class="muted small">{esc(avg_sub)}</p></div>',
        f'<div class="kpi"><p class="muted small l">Written reviews</p><p class="v">{n}</p><p class="muted small">{esc(written_sub)}</p></div>',
        f'<div class="kpi"><p class="muted small l">Negative reviews</p><p class="v" style="color:#C2410C">{100 * neg_n / n:.0f}%</p><p class="muted small">{neg_n} reviews (AI sentiment)</p></div>',
    ]
    if result.has_owner_answers:
        unanswered = df[neg_mask & (df["answered"] == False)].sort_values("date", ascending=False, na_position="last")  # noqa: E712
        answered_rate = df.loc[neg_mask, "answered"].astype(bool).mean() if neg_mask.any() else None
        rate_txt = "no negative review" if answered_rate is None else f"{100 * answered_rate:.0f}% reply rate on complaints"
        kpis.append(f'<div class="kpi alert"><p class="small l" style="font-weight:600">Complaints left unanswered</p>'
                    f'<p class="v">{len(unanswered)}</p><p class="small s">{rate_txt}</p></div>')
    else:
        unanswered = df[neg_mask].sort_values("date", ascending=False, na_position="last")

    # ---- AI diagnosis (always computed on the whole dataset)
    diag = (f'<div class="card"><div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:8px">'
            f'<h2>AI diagnosis</h2><span class="muted small">written by the language model from all reviews</span></div>'
            f'{_diagnosis_html(result.summary)}</div>')

    # ---- charts
    table = theme_breakdown(df, result.themes)
    sent_parts = [("Positive", pos_n, POS), ("Neutral", neu_n, NEU), ("Negative", neg_n, NEG)]
    sentiment_card = (f'<div class="card"><h3>Sentiment of written reviews</h3><p class="muted small">{n} reviews · AI sentiment</p>'
                      f'<div class="donut">{donut_svg(sent_parts, f"{100 * pos_n / n:.0f}%", "positive")}'
                      f'{legend_html(sent_parts)}</div></div>')

    t_mentions = table[table["mentions"] > 0].sort_values("mentions", ascending=False)
    top = t_mentions.head(5)
    theme_parts = [(r.theme, r.mentions, THEME_SHADES[i]) for i, r in enumerate(top.itertuples())]
    rest = int(t_mentions["mentions"].iloc[5:].sum())
    if rest:
        theme_parts.append(("Other themes", rest, THEME_SHADES[5]))
    total_mentions = int(t_mentions["mentions"].sum())
    theme_card = (f'<div class="card"><h3>Share of mentions by theme</h3><p class="muted small">Which topics dominate the conversation</p>'
                  + (f'<div class="donut">{donut_svg(theme_parts, str(total_mentions), "mentions")}'
                     f'{legend_html(theme_parts, lambda v, t: f"{100 * v / t:.0f}%")}</div>'
                     if theme_parts else '<p class="notice" style="margin-top:14px">No theme detected in this selection.</p>')
                  + "</div>")

    use_all = (theme in (None, ALL_THEMES)) and (stars in (None, ALL_STARS))
    points, unit, source = _trend_points(result, df, period, use_all)
    if points is not None:
        trend_card = (f'<div class="card wide"><div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px">'
                      f'<h3>Rating and complaints over time</h3><div class="small muted" style="display:flex;gap:14px">'
                      f'<span><i class="sw" style="background:{ACCENT_DARK};height:3px;width:16px"></i> Average stars</span>'
                      f'<span><i class="sw" style="background:#F9C5AA"></i> % of 1 to 2-star ratings</span></div></div>'
                      f'<p class="muted small" style="margin:2px 0 10px">Per {unit} · {esc(source)}</p>{trend_svg(points, unit)}</div>')
    else:
        trend_card = ('<div class="card wide"><h3>Rating and complaints over time</h3>'
                      '<p class="notice" style="margin-top:10px">Not enough dated ratings in this selection to draw a trend.</p></div>')

    matrix_card = (f'<div class="card"><h3>Priority matrix</h3><p class="muted small" style="margin-bottom:12px">'
                   f'How often a theme is mentioned vs how people feel about it</p>{matrix_svg(table)}</div>')

    rated = table[table["avg_rating"].notna() & (table["mentions"] > 0)].sort_values("avg_rating", ascending=False)
    if not rated.empty:
        stars_theme_card = ('<div class="card"><h3>Average stars by theme</h3><p class="muted small">Stars given when a theme is mentioned</p>'
                            + hbar_rows([(r.theme, r.avg_rating / 5, 0, POS if r.avg_rating >= 4 else NEG if r.avg_rating < 3 else ACCENT_DARK,
                                          f"{r.avg_rating:.1f}") for r in rated.itertuples()]) + "</div>")
    else:
        stars_theme_card = ""

    themes_card = ('<div class="card" style="flex:3 1 420px;min-width:0"><div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px">'
                   '<h2>What people talk about</h2><div class="small muted" style="display:flex;gap:12px">'
                   f'<span><i class="sw" style="background:{POS}"></i> Positive</span><span><i class="sw" style="background:{NEU}"></i> Neutral</span>'
                   f'<span><i class="sw" style="background:{NEG}"></i> Negative</span></div></div>{stacked_rows(table)}'
                   '<p class="muted small" style="margin-top:12px">Bar length = number of reviews mentioning the theme.</p></div>')

    src = df["rating"] if df["rating"].notna().any() else df["pred_stars"]
    counts = src.round().value_counts().reindex(range(1, 6), fill_value=0)
    if not filtered and result.reviews.attrs.get("all_ratings"):
        all_r = pd.Series([r for _, r in result.reviews.attrs["all_ratings"]])
        counts = all_r.round().value_counts().reindex(range(1, 6), fill_value=0)
    cmax = counts.max() or 1
    star_rows = hbar_rows([(f"{k}★", v / cmax, 0, POS if k >= 4 else NEG if k <= 2 else "#98A2B3", str(int(v)))
                           for k, v in sorted(counts.items(), reverse=True)])
    ev = evaluate(df)
    reliability = (f'<div style="margin-top:16px;padding-top:12px;border-top:1px solid #EEF0F3"><p class="muted small">AI reliability on these reviews</p>'
                   f'<p style="font-size:14px;margin-top:4px"><b>{ev["accuracy_3_classes"]:.0%}</b> agreement with customer stars '
                   f'<span class="muted">vs {ev["baseline_majority_class"]:.0%} for a naive baseline</span></p></div>') if ev else ""
    stars_card = (f'<div class="card" style="flex:2 1 280px;min-width:0"><h2>Star ratings</h2>'
                  f'<p class="muted small">{"all ratings" if not filtered else "this selection"}</p>{star_rows}{reliability}</div>')

    # ---- complaints
    title = "Complaints without an answer" if result.has_owner_answers else "Negative reviews"
    caution = ""
    if result.has_owner_answers and s.get("owner_answers_all_empty"):
        caution = ('<p class="notice" style="margin-bottom:12px">No owner reply at all was found in this file: either the business '
                   'never answers, or the export did not include replies. Check on Google Maps.</p>')
    elif not result.has_owner_answers:
        caution = ('<p class="notice" style="margin-bottom:12px">This file has no owner-reply column, so all negative reviews are listed.</p>')
    if unanswered.empty:
        complaints_body = '<p class="notice">No complaint left unanswered in this selection.</p>'
    else:
        first = "".join(_review_card(result, i, r, True) for i, r in unanswered.head(show_cards).iterrows())
        others = unanswered.iloc[show_cards:]
        more = (f'<details><summary>Show the {len(others)} other complaints</summary><div class="stack" style="gap:12px;margin-top:12px">'
                + "".join(_review_card(result, i, r, True) for i, r in others.iterrows()) + "</div></details>") if len(others) else ""
        hint = ('<p class="muted small" style="margin-top:10px">Draft a reply for any review with the reply assistant below (use its # number).</p>')
        complaints_body = f'<div class="stack" style="gap:12px">{first}</div>{more}{hint}'
    complaints = (f'<div class="card"><div style="display:flex;align-items:center;gap:10px;margin-bottom:14px"><h2>{title}</h2>'
                  f'<span class="pill" style="color:#9A3412;background:#FFEDE3">{len(unanswered)}</span></div>{caution}{complaints_body}</div>')

    table_all = all_reviews_frame(result, period, stars, theme)
    n_text = int((table_all["Review"] != "").sum())
    all_reviews = (f'<div class="card"><details open><summary style="all:unset;cursor:pointer;display:flex;'
                   f'align-items:center;gap:10px;margin-bottom:12px"><h2>All reviews</h2><span class="pill" '
                   f'style="color:#005A87;background:#E5F5FC">{len(table_all)}</span><span class="muted small">'
                   f'{n_text} with text · {len(table_all) - n_text} star-only · newest first · click to fold</span>'
                   f'</summary>{all_reviews_html(table_all)}</details></div>')

    return f"""<div class="rp stack">
{header}{filter_note}
<div class="kpis">{''.join(kpis)}</div>
{diag}
<div><h2 style="font-size:20px">Insights</h2><p class="muted small">Every chart follows the filters.</p></div>
<div class="grid">{sentiment_card}{theme_card}{trend_card}{matrix_card}{stars_theme_card}</div>
<div style="display:flex;flex-wrap:wrap;gap:20px">{themes_card}{stars_card}</div>
{complaints}
{all_reviews}
<p class="muted small" style="text-align:center">Reviewer identities are never stored. AI outputs are drafts to be checked by a human.</p>
</div>"""
