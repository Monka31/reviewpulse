"""ReviewPulse web app (Gradio).

Run:
    python app.py            # local, http://127.0.0.1:7860
    python app.py --share    # also creates a temporary public link (automatic in Colab)

Layout: a "New analysis" panel on the left, and on the right an HTML dashboard
(reviewpulse/dashboard.py) with filters, followed by the reply assistant, the model
evaluation and the export tools.
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
from reviewpulse import dashboard as dash
from reviewpulse.analysis import review_label
from reviewpulse.evaluation import evaluate, evaluation_markdown

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
NO_SAMPLE = "(none: use my uploaded file)"
LANGUAGES = {"EN": "English", "FR": "French"}

# ESSEC-like light blue palette
BLUE = gr.themes.Color(c50="#E5F5FC", c100="#C6E9F8", c200="#8FD4F2", c300="#57BFEB", c400="#1FAAE4",
                       c500="#00A0E0", c600="#0077B3", c700="#005A87", c800="#00415F", c900="#002C41",
                       c950="#001A27", name="essec_blue")

THEME = gr.themes.Base(
    primary_hue=BLUE, neutral_hue="slate", radius_size="lg",
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
).set(
    body_background_fill="#F6F7F9",
    block_border_color="#E4E7EC",
    block_radius="14px",
    block_shadow="none",
    block_title_text_weight="600",
    block_label_text_weight="600",
    input_border_color="#D0D5DD",
    input_background_fill="#FFFFFF",
    input_radius="10px",
    button_primary_background_fill="#0077B3",
    button_primary_background_fill_hover="#005A87",
    button_primary_text_color="#FFFFFF",
    button_large_radius="11px",
    checkbox_label_background_fill="#FFFFFF",
    checkbox_label_border_color="#D0D5DD",
    checkbox_label_background_fill_selected="#E5F5FC",
    checkbox_label_border_color_selected="#0077B3",
    checkbox_label_text_color_selected="#005A87",
)

APP_CSS = dash.CSS + """
footer{display:none !important}
.gradio-container{max-width:1400px !important;margin:0 auto !important}
#rp-topbar{background:#fff;border:1px solid #E4E7EC;border-radius:14px;padding:12px 18px}
#rp-panel{background:#fff;border:1px solid #E4E7EC;border-radius:16px;padding:18px 18px 14px;gap:14px}
#rp-run button,#rp-run{font-size:15px;font-weight:600;min-height:48px}
#rp-filters{background:#fff;border:1px solid #E4E7EC;border-radius:14px;padding:8px 12px;align-items:end}
.rp-pills .wrap label{border-radius:20px !important;padding:6px 12px !important}
.rp-empty{background:#fff;border:1px dashed #D0D5DD;border-radius:16px;padding:60px 24px;text-align:center;color:#5B6474}
"""

TOPBAR = """<div class="rp" style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px">
<div style="display:flex;align-items:center;gap:10px">
<div style="width:34px;height:34px;border-radius:9px;background:#00A0E0;display:flex;align-items:center;justify-content:center">
<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="2 12 7 12 10 5 14 19 17 12 22 12"></polyline></svg></div>
<span style="font-family:'Plus Jakarta Sans',Inter,sans-serif;font-weight:800;font-size:20px;letter-spacing:-.3px">ReviewPulse</span>
<span style="font-size:12px;font-weight:600;color:#3A4556;background:#EEF1F5;padding:3px 9px;border-radius:20px">Review intelligence</span></div>
<div class="muted small">{hardware}</div></div>"""

EMPTY = """<div class="rp rp-empty"><h2 style="margin-bottom:6px">Drop a review file to start</h2>
<p>Upload an Outscraper Excel/CSV export (or pick a dataset), choose the business type and click <b>Analyze reviews</b>.
The dashboard, charts and reply drafts will appear here.</p></div>"""


def sample_files() -> list[str]:
    return sorted(p.name for p in DATA_DIR.glob("*.csv"))


def reply_candidates(result, period=dash.ALL_TIME, stars=dash.ALL_STARS, theme=dash.ALL_THEMES):
    """Negative reviews offered in the reply assistant, unanswered ones first."""
    df = dash.apply_filters(result, period, stars, theme)
    neg = df[(df["sentiment"] == "negative") | (df["rating"] <= 2)]
    if result.has_owner_answers:
        neg = neg.sort_values(["answered", "date"], ascending=[True, False], na_position="last")
    return [(review_label(row), int(idx)) for idx, row in neg.iterrows()]


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


# ---------------------------------------------------------------- callbacks
def on_type_change(business_type):
    return ", ".join(config.THEME_PRESETS[business_type])


def run_analysis(file, sample, business_name, business_type, themes_text, language, max_reviews,
                 with_summary, n_replies, progress=gr.Progress()):
    source = file if file is not None else (DATA_DIR / sample if sample and sample != NO_SAMPLE else None)
    if source is None:
        raise gr.Error("Upload a review file (Excel or CSV) or pick a dataset.")
    if hasattr(source, "name") and not isinstance(source, Path):
        source = source.name
    themes = [t.strip() for t in themes_text.split(",") if t.strip()] or config.THEME_PRESETS[business_type]
    if len(themes) > 10:
        raise gr.Error("Use at most 10 themes (each theme adds processing time).")
    try:
        result = rp.run_pipeline(source, business_name=business_name.strip() or None,
                                 business_type=business_type, themes=themes,
                                 max_reviews=int(max_reviews), summary=with_summary,
                                 language=LANGUAGES.get(language, "English"), n_replies=int(n_replies),
                                 progress=lambda f, d="": progress(f, desc=d))
    except rp.ReviewFileError as exc:
        raise gr.Error(str(exc))

    ev = evaluate(result.reviews)
    choices = reply_candidates(result)
    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_path = OUTPUT_DIR / f"{rp.data.slugify(result.business_name)}_analyzed.csv"
    cols = [c for c in result.reviews.columns if not c.startswith("score::")]
    result.reviews[cols].assign(themes=result.reviews["themes"].map("; ".join)).to_csv(
        csv_path, index_label="id", encoding="utf-8-sig")

    return (
        result,
        dash.render_dashboard(result),
        gr.update(visible=True),
        gr.update(choices=dash.period_choices(result), value=dash.ALL_TIME),
        gr.update(value=dash.ALL_STARS),
        gr.update(choices=dash.theme_choices(result), value=dash.ALL_THEMES),
        gr.update(visible=True),
        gr.update(choices=choices, value=choices[0][1] if choices else None),
        evaluation_markdown(ev),
        charts.confusion_chart(ev["confusion_stars"], "Actual vs predicted stars") if ev else None,
        display_table(result.reviews),
        str(csv_path),
    )


def refresh(result, period, stars, theme):
    if result is None:
        return EMPTY, gr.update()
    choices = reply_candidates(result, period, stars, theme)
    return (dash.render_dashboard(result, period, stars, theme),
            gr.update(choices=choices, value=choices[0][1] if choices else None))


def reset_filters():
    return dash.ALL_TIME, dash.ALL_STARS, dash.ALL_THEMES


def show_review(result, idx):
    if result is None or idx is None:
        return ""
    row = result.reviews.loc[int(idx)]
    stars = f"{int(row['rating'])}★" if pd.notna(row["rating"]) else "no rating"
    existing = result.replies.get(int(idx))
    note = "\n\n_A draft already exists for this review: it is shown below._" if existing else ""
    quoted = "\n".join("> " + line for line in row["text"].splitlines())
    return f"**#{idx} · {stars} · {', '.join(row['themes']) or 'no theme'}**\n\n{quoted}{note}"


def current_reply(result, idx):
    if result is None or idx is None:
        return ""
    return result.replies.get(int(idx), "")


def draft_reply(result, idx, period, stars, theme, progress=gr.Progress()):
    if result is None:
        raise gr.Error("Run an analysis first.")
    if idx is None:
        raise gr.Error("Pick a review in the list.")
    progress(0.2, desc="Writing the reply")
    result.replies.pop(int(idx), None)  # "Draft" always writes a fresh version
    reply = rp.generate_replies(result, rp.get_backend(), [int(idx)])[int(idx)]
    return reply, dash.render_dashboard(result, period, stars, theme)


def export(result, n_replies, progress=gr.Progress()):
    if result is None:
        raise gr.Error("Run an analysis first.")
    idx = result.unanswered_negative().head(int(n_replies)).index.tolist()
    if idx:
        progress(0.1, desc=f"Drafting up to {len(idx)} replies")
        rp.generate_replies(result, rp.get_backend(), idx)
    progress(0.9, desc="Building the report")
    path = rp.export_report(result, out_dir=ROOT / "docs", max_replies=int(n_replies))
    return str(path), (f"Report saved as `docs/reports/{path.name}`. Upload it to the `docs/reports/` folder "
                       "of the GitHub repository (with `docs/index.html`) to publish it on GitHub Pages.")


# ---------------------------------------------------------------- layout
def build_app() -> gr.Blocks:
    types = list(config.THEME_PRESETS)
    samples = [NO_SAMPLE] + sample_files()
    real = [f for f in samples if f.startswith("reviews_")]
    backend = rp.get_backend()
    hardware = "GPU ready" if getattr(backend, "has_gpu", False) else "Running on CPU: AI steps are slower"

    with gr.Blocks(title="ReviewPulse", fill_width=True) as demo:
        state = gr.State(None)
        gr.HTML(TOPBAR.format(hardware=hardware), elem_id="rp-topbar", padding=False)

        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=320, elem_id="rp-panel"):
                gr.HTML('<div class="rp"><h2>New analysis</h2><p class="muted small" style="margin-top:4px">'
                        'Drop the reviews of any business. Columns are detected automatically.</p></div>',
                        padding=False)
                file = gr.File(label="Review file (Outscraper Excel or CSV)",
                               file_types=[".csv", ".tsv", ".xlsx", ".xls"], height=130)
                sample = gr.Dropdown(samples, value=(real or samples[1:] or [NO_SAMPLE])[0],
                                     label="...or a dataset from the project")
                business_name = gr.Textbox(label="Business name", placeholder="Detected from the file if empty")
                business_type = gr.Radio(types, value=config.DEFAULT_BUSINESS_TYPE, label="Business type",
                                         elem_classes="rp-pills")
                themes = gr.Textbox(value=", ".join(config.THEME_PRESETS[config.DEFAULT_BUSINESS_TYPE]),
                                    label="Themes to detect (comma-separated)", lines=3)
                language = gr.Radio(list(LANGUAGES), value="EN", label="Summary language", elem_classes="rp-pills")
                with gr.Accordion("Advanced settings", open=False):
                    max_reviews = gr.Slider(20, 2000, value=config.MAX_REVIEWS_DEFAULT, step=10,
                                            label="Max reviews (most recent first)")
                    n_replies = gr.Slider(0, 15, value=5, step=1,
                                          label="Reply drafts written during the analysis")
                    with_summary = gr.Checkbox(value=True, label="Write the AI diagnosis")
                run_btn = gr.Button("Analyze reviews", variant="primary", size="lg", elem_id="rp-run")
                gr.HTML(f'<p class="rp muted small" style="text-align:center">About 1 to 2 minutes for 300 reviews '
                        f'on a GPU.<br>{backend.describe()}</p>', padding=False)

            with gr.Column(scale=3, min_width=360):
                with gr.Row(elem_id="rp-filters", visible=False) as filters_row:
                    period = gr.Dropdown([dash.ALL_TIME], value=dash.ALL_TIME, label="Period", min_width=150)
                    stars = gr.Dropdown(list(dash.STAR_FILTERS), value=dash.ALL_STARS, label="Stars", min_width=150)
                    theme = gr.Dropdown([dash.ALL_THEMES], value=dash.ALL_THEMES, label="Theme", min_width=180)
                    reset_btn = gr.Button("Reset filters", size="md", min_width=120)
                dashboard = gr.HTML(EMPTY, padding=False)

                with gr.Column(visible=False) as tools:
                    with gr.Accordion("Reply assistant", open=True):
                        gr.Markdown("Pick a negative review and let the AI draft a public reply, in the language "
                                    "of the review. Always read and adapt it before posting.")
                        review_pick = gr.Dropdown(choices=[], label="Review to answer (unanswered first)")
                        review_view = gr.Markdown()
                        reply_btn = gr.Button("Draft a reply", variant="primary")
                        reply_box = gr.Textbox(label="Suggested reply (editable)", lines=6, buttons=["copy"])
                    with gr.Accordion("Model evaluation", open=False):
                        eval_md = gr.Markdown()
                        conf_plot = gr.Plot(show_label=False)
                    with gr.Accordion("All reviews and export", open=False):
                        all_table = gr.Dataframe(wrap=True, interactive=False, max_height=420)
                        csv_file = gr.File(label="Analyzed reviews (CSV)")
                        gr.Markdown("**Publish a report.** Builds a static HTML page with the same dashboard, "
                                    "ready for GitHub Pages (permanent link).")
                        export_n = gr.Slider(0, 25, value=10, step=1, label="Reply drafts included in the report")
                        export_btn = gr.Button("Build the HTML report")
                        export_msg = gr.Markdown()
                        report_file = gr.File(label="Report")

        business_type.change(on_type_change, business_type, themes)
        run_btn.click(
            run_analysis,
            [file, sample, business_name, business_type, themes, language, max_reviews, with_summary, n_replies],
            [state, dashboard, filters_row, period, stars, theme, tools, review_pick, eval_md, conf_plot,
             all_table, csv_file],
        ).then(show_review, [state, review_pick], review_view).then(current_reply, [state, review_pick], reply_box)
        for f in (period, stars, theme):
            f.input(refresh, [state, period, stars, theme], [dashboard, review_pick])
        reset_btn.click(reset_filters, None, [period, stars, theme]).then(
            refresh, [state, period, stars, theme], [dashboard, review_pick])
        review_pick.change(show_review, [state, review_pick], review_view).then(
            current_reply, [state, review_pick], reply_box)
        reply_btn.click(draft_reply, [state, review_pick, period, stars, theme], [reply_box, dashboard])
        export_btn.click(export, [state, export_n], [report_file, export_msg])
    return demo


def launch(share: bool = False, port: int | None = None, **kwargs):
    return build_app().queue().launch(share=share, server_port=port, theme=THEME, css=APP_CSS,
                                      head=dash.FONTS_LINK, **kwargs)


def main():
    parser = argparse.ArgumentParser(description="ReviewPulse web app")
    parser.add_argument("--share", action="store_true", help="create a temporary public link")
    parser.add_argument("--port", type=int, default=None, help="default: first free port from 7860")
    args = parser.parse_args()
    in_colab = "google.colab" in sys.modules or os.path.exists("/content")
    launch(share=args.share or in_colab, port=args.port)


if __name__ == "__main__":
    main()
