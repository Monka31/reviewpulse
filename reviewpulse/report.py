"""Static HTML reports, published for free on GitHub Pages (permanent link).

Each analysis can be exported as one self-contained HTML page (charts load Plotly from a CDN).
`docs/index.html` lists every published report, using `docs/reports/manifest.json`.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import markdown as md
import pandas as pd

from . import charts, config
from .analysis import AnalysisResult
from .data import slugify
from .evaluation import evaluate, evaluation_markdown

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--text:#1f2933;--muted:#5f6b7a;--line:#e3e7ec;--accent:#3b5bdb;
--pos:#2f9e5b;--neg:#d64545;--neu:#9aa1a9}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.55 Inter,"Segoe UI",Arial,sans-serif}
main{max-width:1080px;margin:0 auto;padding:28px 16px 60px}
header h1{margin:0 0 4px;font-size:28px}header p{margin:0;color:var(--muted)}
.brand{font-weight:700;color:var(--accent);letter-spacing:.3px;font-size:13px;text-transform:uppercase}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:22px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .v{font-size:26px;font-weight:700}.kpi .l{color:var(--muted);font-size:13px}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:16px 0}
section h2{margin:0 0 12px;font-size:19px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:760px){.grid2{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600}
.review{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.review .meta{color:var(--muted);font-size:13px;margin-bottom:4px}
.reply{margin-top:10px;background:#f1f4fd;border-left:3px solid var(--accent);padding:10px 12px;border-radius:6px}
.reply b{display:block;font-size:12px;color:var(--accent);text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px}
.tag{display:inline-block;background:#eef1f5;border-radius:20px;padding:1px 9px;font-size:12px;margin-right:4px}
.pos{color:var(--pos)}.neg{color:var(--neg)}footer{color:var(--muted);font-size:13px;margin-top:26px}
.notice{color:var(--muted);font-size:13px}a{color:var(--accent)}
"""


def _fig_html(fig, first: bool) -> str:
    if fig is None:
        return ""
    return fig.to_html(full_html=False, include_plotlyjs="cdn" if first else False,
                       config={"displayModeBar": False, "responsive": True})


def _kpi(value, label) -> str:
    return f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>'


def _rating_only(s: dict) -> str:
    n = s.get("n_rating_only", 0)
    return f" (plus {n} star-only ratings without text)" if n else ""


def _fmt_pct(v):
    return "n/a" if v is None else f"{v:.0f}%"


def build_report_html(result: AnalysisResult, max_replies: int = 10) -> str:
    s = result.stats
    ev = evaluate(result.reviews)
    period = ""
    if s.get("date_min") is not None and pd.notna(s["date_min"]):
        period = f" · {s['date_min']:%b %Y} to {s['date_max']:%b %Y}"

    kpis = [
        _kpi(f"{s['avg_rating']}/5" if s.get("avg_rating") else f"~{s['avg_predicted_stars']}/5",
             "Average rating" if s.get("avg_rating") else "Average predicted rating"),
        _kpi(f'<span class="pos">{s["pct_positive"]:.0f}%</span>', "Positive reviews"),
        _kpi(f'<span class="neg">{s["pct_negative"]:.0f}%</span>', "Negative reviews"),
    ]
    if "reply_rate" in s:
        kpis += [_kpi(_fmt_pct(s.get("reply_rate_negative")), "Negative reviews answered"),
                 _kpi(s["n_unanswered_negative"], "Negative reviews left unanswered")]

    summary = result.summary or ""
    summary_html = md.markdown(summary) if summary else "<p class='notice'>AI summary not generated.</p>"

    theme_rows = "".join(
        f"<tr><td>{html.escape(r.theme)}</td><td>{r.mentions}</td><td class='pos'>{r.positive}</td>"
        f"<td class='neg'>{r.negative}</td><td>{r.net_score:+d}</td></tr>"
        for r in result.theme_table.itertuples()
    )

    unanswered = result.unanswered_negative()
    caution = ("<p class='notice'>No owner reply at all was found in this file: either the business "
               "never answers its reviews, or the export did not include replies.</p>"
               if s.get("owner_answers_all_empty") else "")
    if not result.has_owner_answers:
        unanswered_html = "<p class='notice'>This file has no owner-reply column, so unanswered reviews cannot be detected.</p>"
    elif unanswered.empty:
        unanswered_html = "<p>Every negative review has an answer from the owner. Well done.</p>"
    else:
        blocks = []
        for idx, row in unanswered.head(max_replies).iterrows():
            date = f"{row['date']:%Y-%m-%d}" if pd.notna(row["date"]) else "no date"
            stars = f"{int(row['rating'])}★" if pd.notna(row["rating"]) else ""
            tags = "".join(f"<span class='tag'>{html.escape(t)}</span>" for t in row["themes"])
            reply = result.replies.get(idx)
            reply_html = (f"<div class='reply'><b>Suggested reply (AI draft, to review before posting)</b>"
                          f"{html.escape(reply)}</div>" if reply else "")
            blocks.append(f"<div class='review'><div class='meta'>{date} · {stars} {tags}</div>"
                          f"{html.escape(row['text'])}{reply_html}</div>")
        more = len(unanswered) - max_replies
        extra = f"<p class='notice'>…and {more} more unanswered negative reviews.</p>" if more > 0 else ""
        unanswered_html = caution + "".join(blocks) + extra

    figs = [charts.theme_chart(result), charts.rating_chart(result), charts.trend_chart(result)]
    eval_html = ""
    if ev:
        eval_html = (md.markdown(evaluation_markdown(ev), extensions=["tables"]) +
                     _fig_html(charts.confusion_chart(ev["confusion_classes"], "Confusion matrix (sentiment classes)"), False))
    else:
        eval_html = f"<p class='notice'>{evaluation_markdown(None)}</p>"

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(result.business_name)} · ReviewPulse</title><style>{CSS}</style></head><body><main>
<header><div class="brand">ReviewPulse report</div><h1>{html.escape(result.business_name)}</h1>
<p>{html.escape(result.business_type)} · {s['n_reviews']} written reviews analyzed{_rating_only(s)}{period} · generated {result.created_at}</p></header>
<div class="kpis">{''.join(kpis)}</div>
<section><h2>AI summary and recommendations</h2>{summary_html}</section>
<section><h2>What customers talk about</h2>{_fig_html(figs[0], True)}
<table><tr><th>Theme</th><th>Mentions</th><th>Positive</th><th>Negative</th><th>Net score</th></tr>{theme_rows}</table></section>
<div class="grid2"><section>{_fig_html(figs[1], False)}</section>
<section>{_fig_html(figs[2], False) or "<p class='notice'>Not enough dated reviews for a trend.</p>"}</section></div>
<section><h2>Negative reviews without an answer</h2>{unanswered_html}</section>
<section><h2>Model evaluation</h2>{eval_html}</section>
<footer>Generated with ReviewPulse. Sentiment: {config.SENTIMENT_MODEL}. Themes (zero-shot): {config.ZERO_SHOT_MODEL}.
Text generation: {html.escape(result.model_info.split('LLM: ')[-1].split(' ·')[0].strip('`'))}.
AI outputs can be wrong: replies are drafts to be reviewed by a human. Reviewer identities are not stored.</footer>
</main></body></html>"""


def export_report(result: AnalysisResult, out_dir: str | Path = "docs", max_replies: int = 10) -> Path:
    """Write docs/reports/<slug>.html and refresh docs/index.html. Returns the report path."""
    out_dir = Path(out_dir)
    reports = out_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    slug = slugify(result.business_name)
    path = reports / f"{slug}.html"
    path.write_text(build_report_html(result, max_replies=max_replies), encoding="utf-8")

    manifest_path = reports / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    manifest = [m for m in manifest if m["slug"] != slug]
    manifest.append({"slug": slug, "name": result.business_name, "type": result.business_type,
                     "reviews": result.stats["n_reviews"], "created_at": result.created_at,
                     "avg_rating": result.stats.get("avg_rating"),
                     "pct_negative": result.stats["pct_negative"]})
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    write_index(out_dir, manifest)
    return path


def write_index(out_dir: Path, manifest: list[dict]) -> Path:
    cards = "".join(
        f"<a class='kpi' href='reports/{m['slug']}.html' style='text-decoration:none;color:inherit'>"
        f"<div class='v' style='font-size:19px'>{html.escape(m['name'])}</div>"
        f"<div class='l'>{html.escape(m['type'])} · {m['reviews']} reviews · "
        f"{m['pct_negative']:.0f}% negative · {m['created_at']}</div></a>"
        for m in sorted(manifest, key=lambda m: m["name"].lower())
    ) or "<p class='notice'>No report published yet.</p>"
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ReviewPulse</title>
<style>{CSS}</style></head><body><main><header><div class="brand">ReviewPulse</div>
<h1>Turn hundreds of reviews into clear actions</h1>
<p>AI analysis of customer reviews: sentiment, themes, unanswered complaints and suggested replies.</p></header>
<section><h2>Published reports</h2><div class="kpis">{cards}</div></section>
<section><h2>Run it yourself</h2><p>The full application (upload any review file, generate replies on demand)
runs for free in Google Colab. See the project README on GitHub for the one-click link.</p></section>
<footer>Built with Hugging Face Transformers, Gradio and Plotly.</footer></main></body></html>"""
    path = Path(out_dir) / "index.html"
    path.write_text(page, encoding="utf-8")
    return path
