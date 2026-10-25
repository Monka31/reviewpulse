"""Prompts and calls to the LLM: executive summary and reply drafts.

All prompts used by the application are defined in this file, so they can be reported
in the project documentation (documentation/prompts_log.md) exactly as they are used.
"""

from __future__ import annotations

import pandas as pd

from .analysis import AnalysisResult

SUMMARY_SYSTEM_PROMPT = (
    "You are a customer-experience consultant. You analyze online reviews for a business owner "
    "and give short, concrete, evidence-based advice. Never invent facts that are not supported "
    "by the data or the review excerpts you are given."
)

SUMMARY_USER_TEMPLATE = """Business: {business} ({business_type})
Number of reviews analyzed: {n_reviews}
Sentiment: {pct_positive}% positive, {pct_neutral}% neutral, {pct_negative}% negative
{rating_line}{reply_line}
Themes (mentions / positive / negative / net score from -100 to +100):
{theme_lines}

Excerpts of negative reviews:
{negative_excerpts}

Excerpts of positive reviews:
{positive_excerpts}

Write the answer in {language}, in Markdown, with exactly these three sections:
### Strengths
(2 to 3 bullet points, each citing the related theme)
### Areas for improvement
(2 to 3 bullet points, each citing the related theme and what customers complain about)
### 3 priority actions
(a numbered list of 3 concrete actions the owner can take in the next month)
Keep it under 220 words."""

REPLY_SYSTEM_PROMPT = (
    "You write public replies to customer reviews on behalf of a business. Replies are warm, "
    "professional, specific to what the customer wrote, and never defensive."
)

REPLY_USER_TEMPLATE = """REPLY_TASK
Business: {business} ({business_type})
Customer review ({stars}):
\"\"\"{review}\"\"\"

Write the public reply from the business owner.
Rules:
- Write in the SAME LANGUAGE as the customer review.
- 60 to 110 words.
- Thank the customer, acknowledge the specific issue(s) they mention, and say what will be done.
- Do not blame the customer, do not promise refunds or discounts, do not invent facts.
- Invite them to get in touch directly.
- Sign as "The {business} team" (translated if the review is not in English).
Return only the reply text."""


def _excerpts(df: pd.DataFrame, n: int, max_chars: int = 280) -> str:
    if df.empty:
        return "(none)"
    lines = []
    for text in df["text"].head(n):
        text = " ".join(text.split())
        lines.append("- " + (text if len(text) <= max_chars else text[:max_chars] + "…"))
    return "\n".join(lines)


def build_summary_messages(result: AnalysisResult, language: str = "English") -> list[dict]:
    s = result.stats
    df = result.reviews
    rating_line = ""
    if s.get("avg_rating"):
        rating_line = (f"Average public rating: {s['avg_rating']}/5 over {s['n_rows_total']} ratings "
                       f"({s['n_reviews']} with a written review, average {s['avg_rating_written']}/5)\n")
    reply_line = (f"Owner reply rate: {s['reply_rate']}% overall, "
                  f"{s.get('reply_rate_negative')}% on negative reviews\n"
                  if "reply_rate" in s else "")
    theme_lines = "\n".join(
        f"- {r.theme}: {r.mentions} / {r.positive} / {r.negative} / {r.net_score:+d}"
        for r in result.theme_table.itertuples()
    )
    # Most informative excerpts: the most confident predictions, newest first.
    neg = df[df["sentiment"] == "negative"].sort_values(["pred_stars", "pred_confidence"], ascending=[True, False])
    pos = df[df["sentiment"] == "positive"].sort_values(["pred_stars", "pred_confidence"], ascending=[False, False])
    user = SUMMARY_USER_TEMPLATE.format(
        business=result.business_name, business_type=result.business_type,
        n_reviews=s["n_reviews"], pct_positive=s["pct_positive"], pct_neutral=s["pct_neutral"],
        pct_negative=s["pct_negative"], rating_line=rating_line, reply_line=reply_line,
        theme_lines=theme_lines, negative_excerpts=_excerpts(neg, 8),
        positive_excerpts=_excerpts(pos, 5), language=language,
    )
    return [{"role": "system", "content": SUMMARY_SYSTEM_PROMPT}, {"role": "user", "content": user}]


def build_reply_messages(result: AnalysisResult, row: pd.Series) -> list[dict]:
    stars = f"{int(row['rating'])}/5 stars" if pd.notna(row["rating"]) else "no star rating"
    user = REPLY_USER_TEMPLATE.format(business=result.business_name, business_type=result.business_type,
                                      stars=stars, review=row["text"][:1500])
    return [{"role": "system", "content": REPLY_SYSTEM_PROMPT}, {"role": "user", "content": user}]


def generate_summary(result: AnalysisResult, backend, language: str = "English") -> str:
    summary = backend.generate([build_summary_messages(result, language)], max_new_tokens=420)[0]
    result.summary = summary
    return summary


def generate_replies(result: AnalysisResult, backend, indices: list[int]) -> dict:
    """Draft replies for the given review indices and store them in result.replies."""
    todo = [i for i in indices if i not in result.replies]
    if todo:
        rows = [result.reviews.loc[i] for i in todo]
        texts = backend.generate([build_reply_messages(result, r) for r in rows], max_new_tokens=200)
        result.replies.update(dict(zip(todo, texts)))
    return {i: result.replies[i] for i in indices}


def fallback_summary(result: AnalysisResult) -> str:
    """Rule-based summary shown when the LLM step is skipped."""
    ins = result.insights
    strengths = ", ".join(ins["strengths"]) or "no clear strength yet (not enough mentions)"
    pains = ", ".join(ins["pain_points"]) or "no recurring complaint"
    return (f"### Strengths\n- Most positive themes: {strengths}\n\n"
            f"### Areas for improvement\n- Themes with the most negative reviews: {pains}\n\n"
            "_Enable the AI summary to get written recommendations._")
