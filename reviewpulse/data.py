"""Loading and normalizing review files.

ReviewPulse accepts any CSV / Excel file that contains a column of review text.
Column names are detected automatically, so exports from Outscraper, Apify, Kaggle
datasets or a hand-made spreadsheet all work without editing.

Normalized columns:
    place, date, rating, text, owner_answer, answered
"""

from __future__ import annotations

import html
import io
import re
from pathlib import Path

import pandas as pd

# Possible source column names, matched case-insensitively. First match wins.
# Review-level names come first: Outscraper exports also contain place-level columns
# ("rating" = average of the place, "reviews" = total count) that must not be used.
COLUMN_ALIASES = {
    "text": ["text", "review_text", "review", "content", "comment", "body",
             "texte", "avis", "commentaire", "review text"],
    "rating": ["review_rating", "stars", "rating", "score", "note", "star_rating",
               "etoiles", "étoiles"],
    "date": ["date", "review_datetime_utc", "publishedatdate", "published_at", "time",
             "timestamp", "review_date", "created_at"],
    "owner_answer": ["owner_answer", "responsefromownertext", "owner_response", "reply",
                     "response", "reponse", "réponse", "reponse_proprietaire"],
    "place": ["place", "name", "title", "business", "business_name", "etablissement",
              "établissement", "lieu"],
}

# These columns are personal data about reviewers. They are dropped on load (GDPR).
PERSONAL_DATA_COLUMNS = {"author_title", "author_link", "author_id", "author_image",
                         "name_of_reviewer", "reviewerid", "reviewerurl", "reviewerphotourl",
                         "user_id", "author", "reviewer"}


class ReviewFileError(ValueError):
    """Raised when a file cannot be turned into a usable review table."""


def _read_table(source) -> pd.DataFrame:
    """Read CSV/TSV/Excel from a path or a file-like object, guessing separator and encoding."""
    name = str(getattr(source, "name", source)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(source)

    raw = Path(source).read_bytes() if not hasattr(source, "read") else source.read()
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    # Pick the separator from the header line: "," by default, ";" for French Excel exports, tab for TSV.
    header = text.splitlines()[0] if text else ""
    sep = max([",", ";", "\t"], key=header.count) if any(c in header for c in ",;\t") else ","
    return pd.read_csv(io.StringIO(text), sep=sep)


def _find_column(columns, aliases):
    lookup = {c.lower().strip(): c for c in columns}
    for alias in aliases:
        if alias in lookup:
            return lookup[alias]
    return None


def _parse_rating(series: pd.Series) -> pd.Series:
    """Accept 4, '4', '4.0', '4 stars', '4/5', '4 étoiles'."""
    if pd.api.types.is_numeric_dtype(series):
        values = series.astype(float)
    else:
        values = series.astype(str).str.extract(r"(\d+(?:[.,]\d+)?)")[0].str.replace(",", ".")
        values = pd.to_numeric(values, errors="coerce")
    return values.where(values.between(1, 5))


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return str(value).strip().lower() in {"", "nan", "none", "null"}


def _clean_text(value) -> str:
    """Remove HTML left by exports (<br>, &amp;...) and normalize whitespace."""
    if _is_blank(value):
        return ""
    text = re.sub(r"<br\s*/?>", "\n", str(value), flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def load_reviews(source, max_reviews: int | None = None, place_name: str | None = None) -> pd.DataFrame:
    """Load a review file and return a normalized DataFrame.

    Args:
        source: path or file-like object (CSV, TSV or Excel).
        max_reviews: keep at most this many reviews (most recent first when dates exist).
        place_name: business name to use when the file has no place column.
    """
    try:
        raw = _read_table(source)
    except Exception as exc:  # pragma: no cover - message is what matters
        raise ReviewFileError(f"Could not read the file: {exc}") from exc

    raw = raw.drop(columns=[c for c in raw.columns if c.lower() in PERSONAL_DATA_COLUMNS])
    cols = {key: _find_column(raw.columns, aliases) for key, aliases in COLUMN_ALIASES.items()}
    if cols["text"] is None:
        raise ReviewFileError(
            "No review text column found. Rename the column that holds the reviews to 'text'. "
            f"Columns in your file: {', '.join(map(str, raw.columns))}"
        )

    df = pd.DataFrame()
    df["text"] = raw[cols["text"]].astype(str).str.strip()
    df["rating"] = _parse_rating(raw[cols["rating"]]) if cols["rating"] else float("nan")
    df["date"] = (pd.to_datetime(raw[cols["date"]], errors="coerce", utc=True).dt.tz_localize(None)
                  if cols["date"] else pd.NaT)
    df["place"] = raw[cols["place"]].astype(str) if cols["place"] else (place_name or "Business")

    has_answer_column = cols["owner_answer"] is not None
    if has_answer_column:
        answers = raw[cols["owner_answer"]]
        df["owner_answer"] = answers.where(~answers.map(_is_blank), None)
        df["answered"] = ~answers.map(_is_blank)
    else:
        df["owner_answer"] = None
        df["answered"] = pd.NA

    df["text"] = df["text"].map(_clean_text)

    # Keep the full picture before dropping star-only reviews (Google lets people rate without writing).
    totals = {
        "n_rows_total": int(len(df)),
        "n_rating_only": int(df["text"].map(_is_blank).sum()),
        "avg_rating_all": round(float(df["rating"].mean()), 2) if df["rating"].notna().any() else None,
        "owner_answers_all_empty": bool(has_answer_column and not df["answered"].any()),
        # Every (date, stars) pair, star-only reviews included: used for the rating trend chart.
        "all_ratings": [
            (d.isoformat() if pd.notna(d) else None, float(r))
            for d, r in zip(df["date"], df["rating"]) if pd.notna(r)
        ],
    }

    # Clean: drop empty / placeholder texts and exact duplicates.
    df = df[~df["text"].map(_is_blank)]
    df = df[df["text"].str.len() >= 3]
    df = df.drop_duplicates(subset=["text"])

    if df["date"].notna().any():
        df = df.sort_values("date", ascending=False, na_position="last")
    if max_reviews:
        df = df.head(int(max_reviews))

    if df.empty:
        raise ReviewFileError("The file contains no usable review text.")

    df = df.reset_index(drop=True)
    df.attrs.update(totals)
    df.attrs["has_owner_answers"] = has_answer_column
    df.attrs["has_ratings"] = bool(df["rating"].notna().any())
    df.attrs["has_dates"] = bool(df["date"].notna().any())
    return df


def guess_business_name(df: pd.DataFrame, fallback: str = "Business") -> str:
    places = df["place"].dropna()
    places = places[~places.isin(["Business", "nan", ""])]
    return places.mode().iat[0] if not places.empty else fallback


def slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", text.lower()).strip("-")
    return text or "report"
