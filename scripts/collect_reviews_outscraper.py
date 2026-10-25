"""Collect Google Maps reviews with Outscraper and save them as an anonymized CSV.

Two modes:

  1) From the Outscraper API (automatic collection)
       pip install outscraper
       export OUTSCRAPER_API_KEY="your_key"          (Windows: set OUTSCRAPER_API_KEY=your_key)
       python scripts/collect_reviews_outscraper.py --query "ESSEC Business School, Cergy" --limit 500

  2) From a file exported on the Outscraper website (JSON, Excel or CSV)
       python scripts/collect_reviews_outscraper.py --file outscraper_export.xlsx

Output: data/reviews_<place>.csv with only these columns:
    place, date, rating, text, owner_answer
No personal data about reviewers is kept (name, id, photo, profile link), in line with GDPR.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def fetch_from_api(query, limit, language):
    from outscraper import ApiClient  # only needed in API mode

    api_key = os.environ.get("OUTSCRAPER_API_KEY")
    if not api_key:
        sys.exit("Set the OUTSCRAPER_API_KEY environment variable with your Outscraper API key.")
    client = ApiClient(api_key=api_key)
    return client.google_maps_reviews(query, reviews_limit=limit, language=language, sort="newest")


def load_export(path):
    """Read an Outscraper export. JSON is nested (one place with reviews_data);
    Excel/CSV exports are flat (one row per review, place columns repeated)."""
    if str(path).lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [data] if isinstance(data, dict) else data
    flat = pd.read_excel(path) if str(path).lower().endswith((".xlsx", ".xls")) else pd.read_csv(path)
    flat = flat.astype(object).where(flat.notna(), None)
    return [{"name": name, "reviews_data": group.to_dict("records")}
            for name, group in flat.groupby("name", sort=False)]


def iter_places(places):
    for item in places:
        if isinstance(item, list):      # some API versions return one list per query
            yield from item
        else:
            yield item


def to_dataframe(places):
    rows = []
    for place in iter_places(places):
        for r in place.get("reviews_data") or []:
            text = (r.get("review_text") or "").strip()
            # Star-only reviews (no text) are kept: they count in the average rating,
            # and ReviewPulse skips them for the text analysis.
            rows.append({
                "place": place.get("name"),
                "date": r.get("review_datetime_utc"),
                "rating": r.get("review_rating"),
                "text": text,
                "owner_answer": r.get("owner_answer"),
            })
    df = pd.DataFrame(rows, columns=["place", "date", "rating", "text", "owner_answer"])
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y %H:%M:%S", errors="coerce")
    return df.sort_values("date", ascending=False)


def main():
    parser = argparse.ArgumentParser(description="Google Maps reviews (Outscraper) -> anonymized CSV")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--query", help='place to search, e.g. "ESSEC Business School, Cergy" or a Google Maps URL')
    src.add_argument("--file", "--json", dest="file", help="file exported from Outscraper (JSON, XLSX or CSV)")
    parser.add_argument("--limit", type=int, default=500, help="max reviews per place (default 500)")
    parser.add_argument("--language", default="fr", help="review language (default fr)")
    parser.add_argument("--out", help="output CSV path")
    args = parser.parse_args()

    places = fetch_from_api(args.query, args.limit, args.language) if args.query else load_export(args.file)
    df = to_dataframe(places)
    if df.empty:
        sys.exit("No review found.")

    name = df["place"].iloc[0] or "place"
    out = Path(args.out) if args.out else ROOT / "data" / ("reviews_" + re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") + ".csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")   # utf-8-sig: accents display correctly in Excel
    print(f"{len(df)} reviews saved to {out} ({(df['text'] != '').sum()} with text)")
    print(df["rating"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
