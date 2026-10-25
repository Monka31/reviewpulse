"""ReviewPulse web app (Gradio).

Run:
    python app.py            # local, http://127.0.0.1:7860
    python app.py --share    # also creates a temporary public link (automatic in Colab)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import gradio as gr
import pandas as pd

import reviewpulse as rp
from reviewpulse import charts, config
from reviewpulse.analysis import review_label
from reviewpulse.evaluation import evaluate, evaluation_markdown

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
NO_SAMPLE = "(none: use my uploaded file)"


def sample_files() -> list[str]:
    return sorted(p.name for p in DATA_DIR.glob("*.csv"))


# ---------------------------------------------------------------- formatting helpers
def kpi_html(result) -> str:
    s = result.stats
    items = [
        (f"{s['avg_rating']}/5" if s.get("avg_rating") else f"~{s['avg_predicted_stars']}/5",
         f"Average rating ({s['n_rows_total']} ratings)" if s.get("avg_rating") else "Avg predicted rating"),
        (f"{s['n_reviews']}", "Written reviews analyzed"),
        (f"{s['pct_positive']:.0f}%", "Positive"),
        (f"{s['pct_negative']:.0f}%", "Negative"),
    ]
    if "reply_rate" in s:
        rr = s.get("reply_rate_negative")
        items += [("n/a" if rr is None else f"{rr:.0f}%", "Negative reviews answered"),
                  (f"{s['n_unanswered_negative']}", "Negative reviews unanswered")]
    cards = "".join(
        f"<div style='flex:1;min-width:130px;border:1px solid #e3e7ec;border-radius:10px;padding:10px 14px'>"
        f"<div style='font-size:24px;font-weight:700'>{v}</div>"
        f"<div style='color:#5f6b7a;font-size:13px'>{label}</div></div>"
        for v, label in items
    )
    strengths = ", ".join(result.insights["strengths"]) or "n/a"
    pains = ", ".join(result.insights["pain_points"]) or "n/a"
    return (f"<div style='display:flex;flex-wrap:wrap;gap:10px'>{cards}</div>"
            f"<p style='margin-top:10px'><b>Top strengths:</b> {strengths} &nbsp;·&nbsp; "
            f"<b>Main pain points:</b> {pains}</p>")


def display_table(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "id": df.index,
        "date": df["date"].dt.strftime("%Y-%m-%d") if df["date"].notna().any() else "",
        "stars": df["rating"],
        "AI sentiment": df["sentiment"],
        "AI stars": df["pred_stars"],
        "themes": df["themes"].map(", ".join),
        "review": df["text"],
    })
    if df["answered"].notna().any():
        out["answered"] = df["answered"].map({True: "yes", False: "no"}).fillna("")
    return out


def reply_candidates(result):
    """Reviews offered in the reply assistant: unanswered negatives, else all negatives."""
    df = result.unanswered_negative()
    if df.empty:
        df = result.reviews[result.reviews["sentiment"] == "negative"]
    return [(review_label(row), int(idx)) for idx, row in df.iterrows()]


# ---------------------------------------------------------------- callbacks
def on_type_change(business_type):
    return ", ".join(config.THEME_PRESETS[business_type])


def run_analysis(file, sample, business_name, business_type, themes_text, max_reviews,
                 language, with_summary, progress=gr.Progress()):
    source = file if file is not None else (DATA_DIR / sample if sample and sample != NO_SAMPLE else None)
    if source is None:
        raise gr.Error("Upload a review file (CSV or Excel) or pick a sample dataset.")
    if hasattr(source, "name") and not isinstance(source, Path):
        source = source.name  # Gradio gives a temp file object or path
    themes = [t.strip() for t in themes_text.split(",") if t.strip()] or config.THEME_PRESETS[business_type]
    if len(themes) > 10:
        raise gr.Error("Use at most 10 themes (each theme adds processing time).")

    try:
        result = rp.run_pipeline(source, business_name=business_name.strip() or None,
                                 business_type=business_type, themes=themes,
                                 max_reviews=int(max_reviews), summary=with_summary,
                                 language=language, n_replies=0,
                                 progress=lambda f, d="": progress(f, desc=d))
    except rp.ReviewFileError as exc:
        raise gr.Error(str(exc))

    ev = evaluate(result.reviews)
    unanswered = result.unanswered_negative()
    if not result.has_owner_answers:
        unanswered_info = ("This file has no owner-reply column, so unanswered reviews cannot be detected. "
                           "The reply assistant lists all negative reviews instead.")
    else:
        unanswered_info = (f"**{len(unanswered)} negative reviews have no answer from the owner.** "
                           "Unanswered complaints are public and visible to every future customer.")
        if result.stats.get("owner_answers_all_empty"):
            unanswered_info += ("\n\n_No owner reply at all was found in this file: either the business never "
                                "answers, or the export did not include replies. Check on Google Maps._")
    choices = reply_candidates(result)
    csv_path = OUTPUT_DIR / f"{rp.data.slugify(result.business_name)}_analyzed.csv"
    OUTPUT_DIR.mkdir(exist_ok=True)
    export_cols = [c for c in result.reviews.columns if not c.startswith("score::")]
    result.reviews[export_cols].assign(themes=result.reviews["themes"].map("; ".join)).to_csv(
        csv_path, index_label="id", encoding="utf-8-sig")

    return (
        result,
        (f"## {result.business_name}\n{result.business_type} · {result.stats['n_reviews']} written reviews"
         + (f" (plus {result.stats['n_rating_only']} star-only ratings, counted in the average)"
            if result.stats.get("n_rating_only") else "")
         + f" · analyzed {result.created_at}"),
        kpi_html(result),
        result.summary,
        charts.theme_chart(result),
        charts.rating_chart(result),
        charts.trend_chart(result),
        unanswered_info,
        display_table(unanswered) if not unanswered.empty else pd.DataFrame(),
        gr.Dropdown(choices=choices, value=choices[0][1] if choices else None),
        evaluation_markdown(ev),
        charts.confusion_chart(ev["confusion_stars"], "Actual vs predicted stars") if ev else None,
        display_table(result.reviews),
        str(csv_path),
    )


def show_review(result, idx):
    if result is None or idx is None:
        return ""
    row = result.reviews.loc[int(idx)]
    stars = f"{int(row['rating'])}★" if pd.notna(row["rating"]) else "no rating"
    return f"**{stars} · themes: {', '.join(row['themes']) or 'none'}**\n\n> {row['text']}"


def draft_reply(result, idx, progress=gr.Progress()):
    if result is None:
        raise gr.Error("Run an analysis first.")
    if idx is None:
        raise gr.Error("Pick a review in the list.")
    progress(0.2, desc="Writing the reply")
    return rp.generate_replies(result, rp.get_backend(), [int(idx)])[int(idx)]


def export(result, n_replies, progress=gr.Progress()):
    if result is None:
        raise gr.Error("Run an analysis first.")
    idx = result.unanswered_negative().head(int(n_replies)).index.tolist()
    if idx:
        progress(0.1, desc=f"Drafting {len(idx)} replies")
        rp.generate_replies(result, rp.get_backend(), idx)
    progress(0.9, desc="Building the report")
    path = rp.export_report(result, out_dir=ROOT / "docs", max_replies=int(n_replies))
    return str(path), (f"Report saved to `docs/reports/{path.name}`. Commit the `docs/` folder to GitHub "
                       "to publish it on your GitHub Pages site (see the user guide).")


# ---------------------------------------------------------------- layout
def build_app() -> gr.Blocks:
    types = list(config.THEME_PRESETS)
    samples = [NO_SAMPLE] + sample_files()
    with gr.Blocks(title="ReviewPulse") as demo:
        state = gr.State(None)
        gr.Markdown("# ReviewPulse\nTurn hundreds of customer reviews into clear actions: "
                    "sentiment, themes, unanswered complaints and AI-drafted replies.")
        with gr.Row():
            with gr.Column(scale=1, min_width=300):
                file = gr.File(label="1. Review file (CSV or Excel)",
                               file_types=[".csv", ".tsv", ".xlsx", ".xls"])
                real = [f for f in samples if f.startswith("reviews_")]
                sample = gr.Dropdown(samples, value=(real or samples[1:] or [NO_SAMPLE])[0],
                                     label="...or a sample dataset from the data/ folder")
                business_name = gr.Textbox(label="2. Business name (optional)",
                                           placeholder="Detected from the file if empty")
                business_type = gr.Dropdown(types, value=config.DEFAULT_BUSINESS_TYPE, label="3. Business type")
                themes = gr.Textbox(value=", ".join(config.THEME_PRESETS[config.DEFAULT_BUSINESS_TYPE]),
                                    label="Themes to detect (comma-separated, editable)", lines=3)
                max_reviews = gr.Slider(20, 2000, value=config.MAX_REVIEWS_DEFAULT, step=10,
                                        label="Max reviews (most recent first)")
                with_summary = gr.Checkbox(value=True, label="Write an AI summary with recommendations")
                language = gr.Radio(config.OUTPUT_LANGUAGES, value="English", label="Summary language")
                run_btn = gr.Button("Analyze reviews", variant="primary")
                gr.Markdown(f"<small>{rp.get_backend().describe()}</small>")

            with gr.Column(scale=3):
                header = gr.Markdown("## Upload a file or pick a sample, then click **Analyze reviews**.")
                with gr.Tabs():
                    with gr.Tab("Overview"):
                        kpis = gr.HTML()
                        summary = gr.Markdown()
                        theme_plot = gr.Plot(show_label=False)
                        with gr.Row():
                            rating_plot = gr.Plot(show_label=False)
                            trend_plot = gr.Plot(show_label=False)
                    with gr.Tab("Unanswered reviews"):
                        unanswered_info = gr.Markdown()
                        unanswered_table = gr.Dataframe(wrap=True, interactive=False)
                    with gr.Tab("Reply assistant"):
                        gr.Markdown("Pick a negative review and let the AI draft a public reply. "
                                    "Always read and adapt it before posting.")
                        review_pick = gr.Dropdown(choices=[], label="Review to answer")
                        review_view = gr.Markdown()
                        reply_btn = gr.Button("Draft a reply", variant="primary")
                        reply_box = gr.Textbox(label="Suggested reply (editable)", lines=7)
                    with gr.Tab("Model evaluation"):
                        eval_md = gr.Markdown()
                        conf_plot = gr.Plot(show_label=False)
                    with gr.Tab("All reviews"):
                        all_table = gr.Dataframe(wrap=True, interactive=False)
                        csv_file = gr.File(label="Download the analyzed reviews (CSV)")
                    with gr.Tab("Export report"):
                        gr.Markdown("Create a static HTML report (permanent link once published on "
                                    "GitHub Pages). Replies are drafted for the most recent unanswered "
                                    "negative reviews.")
                        n_replies = gr.Slider(0, 25, value=10, step=1, label="Replies to include")
                        export_btn = gr.Button("Build the HTML report", variant="primary")
                        export_msg = gr.Markdown()
                        report_file = gr.File(label="Report")

        business_type.change(on_type_change, business_type, themes)
        run_btn.click(
            run_analysis,
            [file, sample, business_name, business_type, themes, max_reviews, language, with_summary],
            [state, header, kpis, summary, theme_plot, rating_plot, trend_plot, unanswered_info,
             unanswered_table, review_pick, eval_md, conf_plot, all_table, csv_file],
        ).then(show_review, [state, review_pick], review_view)
        review_pick.change(show_review, [state, review_pick], review_view)
        reply_btn.click(draft_reply, [state, review_pick], reply_box)
        export_btn.click(export, [state, n_replies], [report_file, export_msg])
    return demo


def main():
    parser = argparse.ArgumentParser(description="ReviewPulse web app")
    parser.add_argument("--share", action="store_true", help="create a temporary public link")
    parser.add_argument("--port", type=int, default=None, help="default: first free port from 7860")
    args = parser.parse_args()
    in_colab = "google.colab" in sys.modules or os.path.exists("/content")
    build_app().queue().launch(share=args.share or in_colab, server_port=args.port)


if __name__ == "__main__":
    main()
