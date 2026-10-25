"""Central configuration: models, theme presets and analysis settings.

Every model can be overridden with an environment variable, so the pipeline can be
re-run with other Hugging Face checkpoints without touching the code.
"""

import os

# --- Hugging Face models -------------------------------------------------------------
# Multilingual sentiment model: predicts a 1-5 star rating for a review (EN, FR, DE, NL, ES, IT).
SENTIMENT_MODEL = os.environ.get(
    "REVIEWPULSE_SENTIMENT_MODEL", "nlptown/bert-base-multilingual-uncased-sentiment"
)

# Multilingual NLI model used for zero-shot theme classification (no training needed).
ZERO_SHOT_MODEL = os.environ.get(
    "REVIEWPULSE_ZERO_SHOT_MODEL", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
)

# Small open-source instruction-tuned LLM for summaries and reply drafts.
# 3B fits comfortably on a free Colab T4 GPU; on CPU we fall back to the 0.5B version.
LLM_MODEL_GPU = os.environ.get("REVIEWPULSE_LLM_MODEL", "Qwen/Qwen2.5-3B-Instruct")
LLM_MODEL_CPU = os.environ.get("REVIEWPULSE_LLM_MODEL_CPU", "Qwen/Qwen2.5-0.5B-Instruct")

# --- Zero-shot settings ----------------------------------------------------------------
# The hypothesis is in English; the multilingual NLI model handles French reviews against it.
HYPOTHESIS_TEMPLATE = "This review is about {}."
THEME_THRESHOLD = 0.5          # minimum entailment score for a theme to be assigned
MAX_CHARS_FOR_THEMES = 1200    # long reviews are truncated to keep zero-shot fast

# --- Analysis limits -------------------------------------------------------------------
MAX_REVIEWS_DEFAULT = 500
MIN_MENTIONS_FOR_INSIGHT = 3   # a theme needs at least this many mentions to be called a strength/pain point

# --- Theme presets per business type ---------------------------------------------------
# Kept to 6-7 themes: zero-shot cost grows with (number of reviews x number of themes).
THEME_PRESETS = {
    "Restaurant": [
        "food quality",
        "service and staff",
        "price and value",
        "waiting time",
        "cleanliness",
        "atmosphere",
        "menu choice",
    ],
    "School / University": [
        "teaching quality",
        "campus and facilities",
        "admissions",
        "staff and welcome",
        "administration",
        "student life",
        "career opportunities",
        "tuition fees",
    ],
    "Hotel": [
        "room comfort",
        "cleanliness",
        "staff and service",
        "breakfast",
        "location",
        "price and value",
        "noise",
    ],
    "Retail store": [
        "product quality",
        "staff and advice",
        "price",
        "stock availability",
        "checkout and waiting time",
        "store layout",
        "returns and after-sales",
    ],
    "Generic business": [
        "quality",
        "service and staff",
        "price and value",
        "waiting time",
        "cleanliness",
        "atmosphere",
    ],
}

DEFAULT_BUSINESS_TYPE = "Restaurant"

# Language of the AI summary. Reply drafts always use the language of the review itself.
OUTPUT_LANGUAGES = ["English", "French"]
