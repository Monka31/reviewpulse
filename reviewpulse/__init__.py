"""ReviewPulse: turn hundreds of customer reviews into clear, actionable insights."""

from __future__ import annotations

from . import config
from .analysis import AnalysisResult, analyze
from .data import ReviewFileError, guess_business_name, load_reviews
from .evaluation import evaluate
from .llm import fallback_summary, generate_replies, generate_summary
from .models import get_backend
from .report import export_report

__version__ = "1.0.0"


def run_pipeline(source, business_name: str | None = None, business_type: str = config.DEFAULT_BUSINESS_TYPE,
                 themes: list[str] | None = None, max_reviews: int = config.MAX_REVIEWS_DEFAULT,
                 summary: bool = True, language: str = "English", n_replies: int = 0,
                 backend=None, progress=None) -> AnalysisResult:
    """One-call API used by the notebook, the CLI and the app.

    Loads the file, runs sentiment + themes, then optionally the LLM summary and reply drafts
    for the `n_replies` most recent unanswered negative reviews.
    """
    progress = progress or (lambda f, d="": None)
    backend = backend or get_backend()
    df = load_reviews(source, max_reviews=max_reviews, place_name=business_name)
    name = business_name or guess_business_name(df)
    themes = themes or config.THEME_PRESETS.get(business_type, config.THEME_PRESETS["Generic business"])
    result = analyze(df, themes, backend, name, business_type,
                     progress=lambda f, d: progress(0.75 * f, d))
    if summary:
        progress(0.80, "Writing the AI summary")
        generate_summary(result, backend, language)
    else:
        result.summary = fallback_summary(result)
    if n_replies:
        progress(0.90, "Drafting replies")
        idx = result.unanswered_negative().head(n_replies).index.tolist()
        generate_replies(result, backend, idx)
    progress(1.0, "Done")
    return result


__all__ = ["run_pipeline", "load_reviews", "analyze", "evaluate", "export_report", "generate_summary",
           "generate_replies", "get_backend", "AnalysisResult", "ReviewFileError", "config"]
