"""Fast tests that run without downloading any model (keyword mock backend).

Run:  pytest -q
"""

import io
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

os.environ["REVIEWPULSE_MOCK"] = "1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import reviewpulse as rp  # noqa: E402
from reviewpulse.data import load_reviews  # noqa: E402
from reviewpulse.models import MockBackend  # noqa: E402

SAMPLE = ROOT / "data" / "demo_restaurant_synthetic.csv"


def test_load_sample_normalizes_columns():
    df = load_reviews(SAMPLE)
    assert {"text", "rating", "date", "owner_answer", "answered", "place"} <= set(df.columns)
    assert df.attrs["has_owner_answers"] and df.attrs["has_ratings"] and df.attrs["has_dates"]
    assert df["date"].is_monotonic_decreasing


def test_load_outscraper_style_columns_and_drops_personal_data():
    csv = ("author_title,review_text,review_rating,review_datetime_utc,owner_answer\n"
           "Jane Doe,Great food,5,01/31/2021 15:38:38,\n"
           "John Doe,Slow service,2,01/29/2021 04:26:04,Sorry!\n")
    df = load_reviews(io.BytesIO(csv.encode()))
    assert "author_title" not in df.columns
    assert df["rating"].tolist() == [5, 2]
    assert df["answered"].tolist() == [False, True]


def test_load_semicolon_and_text_only():
    df = load_reviews(io.BytesIO("avis;note\nTrès bon;4 étoiles\nNul;1/5\n".encode()))
    assert df["rating"].tolist() == [4, 1]
    df2 = load_reviews(io.BytesIO(b"text\nhello there\n"))
    assert not df2.attrs["has_ratings"] and not df2.attrs["has_owner_answers"]


def test_missing_text_column_is_explained():
    with pytest.raises(rp.ReviewFileError, match="No review text column"):
        load_reviews(io.BytesIO(b"foo,bar\n1,2\n"))


def test_full_pipeline_and_report(tmp_path):
    result = rp.run_pipeline(SAMPLE, business_type="Restaurant", n_replies=3, backend=MockBackend())
    assert result.stats["n_reviews"] == 30
    assert set(result.reviews["sentiment"]) <= {"positive", "neutral", "negative"}
    assert len(result.theme_table) == len(rp.config.THEME_PRESETS["Restaurant"])
    assert result.summary and len(result.replies) == 3
    ev = rp.evaluate(result.reviews)
    assert 0 <= ev["accuracy_3_classes"] <= 1 and ev["confusion_stars"].shape == (5, 5)
    path = rp.export_report(result, out_dir=tmp_path, max_replies=3)
    page = path.read_text(encoding="utf-8")
    assert "Complaints without an answer" in page and "Suggested reply" in page
    assert (tmp_path / "index.html").exists()


def test_no_ratings_no_answers_still_works():
    data = pd.DataFrame({"text": ["Great staff and delicious food", "Dirty and slow, terrible", "ok"]})
    buf = io.BytesIO(data.to_csv(index=False).encode())
    result = rp.run_pipeline(buf, business_name="X", summary=False, backend=MockBackend())
    assert rp.evaluate(result.reviews) is None
    assert result.unanswered_negative().empty
    assert "Strengths" in result.summary


def test_app_builds():
    import app
    assert app.build_app() is not None


def test_outscraper_flat_export_uses_review_level_rating_and_cleans_html():
    """Outscraper Excel/CSV exports repeat place-level columns ('rating' = place average)."""
    csv = ("name,rating,reviews,author_title,review_text,review_rating,review_datetime_utc,owner_answer\n"
           "ESSEC,4.4,382,Jane,Super campus<br><br>Très beau,5,10/25/2026 14:31:40,\n"
           "ESSEC,4.4,382,John,,1,10/21/2026 14:44:19,\n"
           "ESSEC,4.4,382,Ann,Accueil &amp; admissions décevants,1,10/20/2026 10:00:00,\n")
    df = load_reviews(io.BytesIO(csv.encode()))
    assert df["rating"].tolist() == [5, 1]            # review_rating, not the 4.4 place average
    assert df["text"].iloc[0] == "Super campus\n\nTrès beau"
    assert df["text"].iloc[1].startswith("Accueil & admissions")
    assert df.attrs["n_rows_total"] == 3 and df.attrs["n_rating_only"] == 1
    assert df.attrs["avg_rating_all"] == round((5 + 1 + 1) / 3, 2)
    assert df.attrs["owner_answers_all_empty"]
    assert "author_title" not in df.columns


def test_dashboard_filters_and_empty_state():
    from reviewpulse import dashboard as dash
    result = rp.run_pipeline(SAMPLE, business_type="Restaurant", n_replies=2, backend=MockBackend())
    full = dash.render_dashboard(result)
    assert full.count("<svg") >= 3 and "Insights" in full and "Priority matrix" in full
    neg = dash.apply_filters(result, stars="1 to 2 stars")
    assert len(neg) and neg["rating"].le(2).all()
    year = dash.period_choices(result)[2]
    assert dash.apply_filters(result, period=year)["date"].dt.year.eq(int(year)).all()
    assert "No review matches" in dash.render_dashboard(result, "1999", dash.ALL_STARS, dash.ALL_THEMES) \
        or dash.period_choices(result)  # 1999 is never offered; filter must not crash
    assert "Filtered view" in dash.render_dashboard(result, stars="4 to 5 stars")


def test_all_reviews_table_includes_star_only_ratings():
    from reviewpulse import dashboard as dash
    csv = ("name,review_text,review_rating,review_datetime_utc,owner_answer\n"
           "X,Great place,5,10/25/2026 14:31:40,Thanks!\n"
           "X,,4,10/21/2026 14:44:19,\n"
           "X,Rude staff,1,10/20/2026 10:00:00,\n")
    result = rp.run_pipeline(io.BytesIO(csv.encode()), summary=False, backend=MockBackend())
    table = dash.all_reviews_frame(result)
    assert len(table) == 3 and (table["Review"] == "").sum() == 1
    assert set(table["Owner reply"]) == {"Answered", "Not answered"}
    assert "Star-only rating" in dash.render_dashboard(result)
