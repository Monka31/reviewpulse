"""Static HTML reports, published for free on GitHub Pages (permanent link).

A report is the same dashboard as the app (reviewpulse/dashboard.py), saved as one
self-contained HTML page (no JavaScript). `docs/index.html` lists every published report,
using `docs/reports/manifest.json`.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import markdown as md

from . import config
from .analysis import AnalysisResult
from .dashboard import CSS, FONTS_LINK, render_dashboard
from .data import slugify
from .evaluation import evaluate, evaluation_markdown

PAGE_CSS = """
body{margin:0;background:#F6F7F9}
.rp-page{max-width:1240px;margin:0 auto;padding:20px 16px 48px}
.rp-top{background:#fff;border:1px solid #E4E7EC;border-radius:14px;padding:12px 18px;margin-bottom:20px;
display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px}
.rp table{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}
.rp th,.rp td{text-align:left;padding:7px 8px;border-bottom:1px solid #E4E7EC}.rp th{color:#5B6474;font-weight:600}
.rp a{color:#0077B3}
.rp .report-card{display:block;text-decoration:none;color:inherit}
.rp .report-card:hover{border-color:#00A0E0}
"""

LOGO = ('<div style="display:flex;align-items:center;gap:10px"><div style="width:32px;height:32px;border-radius:9px;'
        'background:#00A0E0;display:flex;align-items:center;justify-content:center"><svg width="19" height="19" '
        'viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><polyline points="2 12 7 12 10 5 14 19 17 12 22 12"></polyline>'
        '</svg></div><span style="font-family:\'Plus Jakarta Sans\',Inter,sans-serif;font-weight:800;font-size:19px">'
        'ReviewPulse</span></div>')


def _page(title: str, body: str, right: str = "") -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            f'{FONTS_LINK}<style>{CSS}{PAGE_CSS}</style></head><body><div class="rp rp-page">'
            f'<div class="rp-top">{LOGO}<span class="muted small">{right}</span></div>{body}</div></body></html>')


def build_report_html(result: AnalysisResult, max_replies: int = 10) -> str:
    ev = evaluate(result.reviews)
    eval_html = (md.markdown(evaluation_markdown(ev), extensions=["tables"]) if ev
                 else f"<p class='notice'>{evaluation_markdown(None)}</p>")
    llm = result.model_info.split("LLM: ")[-1].split(" ·")[0].strip("`")
    body = (render_dashboard(result, show_cards=max_replies)
            + f'<div class="card" style="margin-top:20px"><h2 style="margin-bottom:8px">Model evaluation</h2>{eval_html}</div>'
            + f'<p class="muted small" style="margin-top:20px;text-align:center">Generated with ReviewPulse on {result.created_at}. '
            f'Sentiment: {config.SENTIMENT_MODEL} · Themes (zero-shot): {config.ZERO_SHOT_MODEL} · '
            f'Text generation: {html.escape(llm)}. <a href="../index.html">All reports</a></p>')
    return _page(f"{result.business_name} · ReviewPulse", body, "Customer review report")


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
        f'<a class="kpi report-card" href="reports/{m["slug"]}.html"><p class="eyebrow">{html.escape(m["type"])}</p>'
        f'<p style="font-family:\'Plus Jakarta Sans\',Inter,sans-serif;font-size:19px;font-weight:700;margin:4px 0">'
        f'{html.escape(m["name"])}</p><p class="muted small">{m["reviews"]} written reviews'
        + (f' · {m["avg_rating"]:.2f}/5' if m.get("avg_rating") else "")
        + f' · {m["pct_negative"]:.0f}% negative · {m["created_at"]}</p></a>'
        for m in sorted(manifest, key=lambda m: m["name"].lower())
    ) or "<p class='notice'>No report published yet.</p>"
    body = f"""<div class="stack">
<div><p class="eyebrow">Review intelligence</p><h1>Turn hundreds of reviews into clear actions</h1>
<p class="muted">AI analysis of customer reviews: sentiment, themes, unanswered complaints and suggested replies.</p></div>
<div class="card"><h2 style="margin-bottom:12px">Published reports</h2><div class="kpis">{cards}</div></div>
<div class="card"><h2 style="margin-bottom:6px">Run it yourself</h2><p>The full application (upload any review file,
filter the dashboard, draft replies on demand) runs for free in Google Colab. See the project README on GitHub
for the one-click link.</p></div>
<p class="muted small" style="text-align:center">Built with Hugging Face Transformers and Gradio.</p></div>"""
    path = Path(out_dir) / "index.html"
    path.write_text(_page("ReviewPulse", body), encoding="utf-8")
    return path
