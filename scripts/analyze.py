"""Command-line analysis: review file -> analyzed CSV + HTML report (for GitHub Pages).

Examples:
    python scripts/analyze.py data/essec_reviews.csv --name "ESSEC Business School" --type "School / University"
    python scripts/analyze.py data/restaurant_reviews.csv --type Restaurant --replies 10 --language French
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import reviewpulse as rp  # noqa: E402
from reviewpulse import config  # noqa: E402
from reviewpulse.data import slugify  # noqa: E402
from reviewpulse.evaluation import evaluate  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", help="CSV or Excel file with one review per row")
    p.add_argument("--name", help="business name (detected from the file if omitted)")
    p.add_argument("--type", default=config.DEFAULT_BUSINESS_TYPE, choices=list(config.THEME_PRESETS))
    p.add_argument("--themes", help='custom comma-separated themes, e.g. "food, service, price"')
    p.add_argument("--max-reviews", type=int, default=config.MAX_REVIEWS_DEFAULT)
    p.add_argument("--replies", type=int, default=10, help="replies to draft for unanswered negative reviews")
    p.add_argument("--language", default="English", choices=config.OUTPUT_LANGUAGES, help="summary language")
    p.add_argument("--no-summary", action="store_true", help="skip the LLM summary (faster)")
    p.add_argument("--site-dir", default=str(ROOT / "docs"), help="GitHub Pages folder")
    args = p.parse_args()

    themes = [t.strip() for t in args.themes.split(",")] if args.themes else None
    start = time.time()
    last = {"desc": None}

    def progress(fraction, desc=""):
        if desc != last["desc"]:
            print(f"[{time.time() - start:5.0f}s] {desc}")
            last["desc"] = desc

    result = rp.run_pipeline(args.file, business_name=args.name, business_type=args.type, themes=themes,
                             max_reviews=args.max_reviews, summary=not args.no_summary,
                             language=args.language, n_replies=args.replies, progress=progress)

    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / f"{slugify(result.business_name)}_analyzed.csv"
    cols = [c for c in result.reviews.columns if not c.startswith("score::")]
    result.reviews[cols].assign(themes=result.reviews["themes"].map("; ".join)).to_csv(
        csv_path, index_label="id", encoding="utf-8-sig")
    report = rp.export_report(result, out_dir=args.site_dir, max_replies=args.replies)

    s = result.stats
    ev = evaluate(result.reviews)
    print(f"\n{result.business_name}: {s['n_reviews']} reviews in {time.time() - start:.0f}s")
    print(f"  positive {s['pct_positive']}% · negative {s['pct_negative']}%")
    if "reply_rate" in s:
        print(f"  unanswered negative reviews: {s['n_unanswered_negative']}")
    if ev:
        print(f"  model accuracy vs customer stars: {ev['accuracy_3_classes']:.0%} "
              f"(baseline {ev['baseline_majority_class']:.0%})")
    print(f"  analyzed CSV: {csv_path}\n  HTML report:  {report}")


if __name__ == "__main__":
    main()
