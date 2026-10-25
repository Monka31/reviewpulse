"""Model backends.

`HFBackend` runs the three Hugging Face models (sentiment, zero-shot themes, LLM).
Models are loaded lazily on first use and cached for the whole session.

`MockBackend` is a tiny keyword-based stand-in used by the automated tests and for
UI development without downloading several GB of models. It is NOT AI and is only
enabled with the environment variable REVIEWPULSE_MOCK=1.
"""

from __future__ import annotations

import os
import re
from typing import Callable

from . import config

ProgressFn = Callable[[float, str], None]


def _noop(_fraction: float, _desc: str = "") -> None:
    pass


class HFBackend:
    name = "Hugging Face models"

    def __init__(self, llm_model: str | None = None):
        import torch  # imported here so the mock path works without torch

        self.torch = torch
        self.device = 0 if torch.cuda.is_available() else -1
        self.has_gpu = self.device == 0
        self.llm_model_name = llm_model or (config.LLM_MODEL_GPU if self.has_gpu else config.LLM_MODEL_CPU)
        self._sentiment = None
        self._zero_shot = None
        self._llm = None
        self._tokenizer = None

    # ---- lazy loaders ----------------------------------------------------------------
    @property
    def sentiment_pipe(self):
        if self._sentiment is None:
            from transformers import pipeline
            self._sentiment = pipeline("sentiment-analysis", model=config.SENTIMENT_MODEL,
                                       device=self.device)
        return self._sentiment

    @property
    def zero_shot_pipe(self):
        if self._zero_shot is None:
            from transformers import pipeline
            self._zero_shot = pipeline("zero-shot-classification", model=config.ZERO_SHOT_MODEL,
                                       device=self.device)
        return self._zero_shot

    def _load_llm(self):
        if self._llm is None:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.llm_model_name, padding_side="left")
            dtype = self.torch.float16 if self.has_gpu else self.torch.float32
            self._llm = AutoModelForCausalLM.from_pretrained(self.llm_model_name, torch_dtype=dtype)
            if self.has_gpu:
                self._llm = self._llm.to("cuda")
            self._llm.eval()
        return self._llm, self._tokenizer

    # ---- tasks ---------------------------------------------------------------------
    def sentiment(self, texts: list[str], batch_size: int = 32,
                  progress: ProgressFn = _noop) -> list[tuple[int, float]]:
        """Return (predicted stars 1-5, confidence) for each text."""
        results = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            out = self.sentiment_pipe(batch, truncation=True, max_length=512, batch_size=batch_size)
            results.extend((int(o["label"].split()[0]), float(o["score"])) for o in out)
            progress(min(1.0, (start + len(batch)) / len(texts)), "Sentiment")
        return results

    def themes(self, texts: list[str], labels: list[str], batch_size: int = 16,
               progress: ProgressFn = _noop) -> list[dict[str, float]]:
        """Return {theme: entailment score} for each text (multi-label)."""
        results = []
        texts = [t[:config.MAX_CHARS_FOR_THEMES] for t in texts]
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            out = self.zero_shot_pipe(batch, candidate_labels=labels, multi_label=True,
                                      hypothesis_template=config.HYPOTHESIS_TEMPLATE,
                                      batch_size=32)  # batches (review, theme) pairs on the GPU
            if isinstance(out, dict):
                out = [out]
            results.extend(dict(zip(o["labels"], map(float, o["scores"]))) for o in out)
            progress(min(1.0, (start + len(batch)) / len(texts)), "Themes")
        return results

    def generate(self, conversations: list[list[dict]], max_new_tokens: int = 350,
                 batch_size: int = 4) -> list[str]:
        """Generate one answer per chat conversation (list of {'role','content'} messages)."""
        model, tok = self._load_llm()
        outputs = []
        for start in range(0, len(conversations), batch_size):
            batch = conversations[start:start + batch_size]
            prompts = [tok.apply_chat_template(c, tokenize=False, add_generation_prompt=True)
                       for c in batch]
            enc = tok(prompts, return_tensors="pt", padding=True).to(model.device)
            enc.pop("token_type_ids", None)  # not used by causal LMs (some tokenizers add it)
            with self.torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                     repetition_penalty=1.05, pad_token_id=tok.eos_token_id)
            new_tokens = gen[:, enc["input_ids"].shape[1]:]
            outputs.extend(t.strip() for t in tok.batch_decode(new_tokens, skip_special_tokens=True))
        return outputs

    def describe(self) -> str:
        hw = "GPU" if self.has_gpu else "CPU (slow: switch Colab to a GPU runtime)"
        return (f"Sentiment: `{config.SENTIMENT_MODEL}` · Themes: `{config.ZERO_SHOT_MODEL}` · "
                f"LLM: `{self.llm_model_name}` · Hardware: {hw}")


class MockBackend:
    """Keyword heuristics for tests and offline UI work. Not used in the real app."""

    name = "Mock backend (tests only, no AI)"
    has_gpu = False
    llm_model_name = "mock"

    POSITIVE = ["excellent", "great", "amazing", "delicious", "friendly", "perfect", "love",
                "good", "nice", "recommend", "super", "parfait", "délicieux", "delicieux",
                "génial", "genial", "bon", "agréable", "agreable", "top", "recommande", "accueillant"]
    NEGATIVE = ["bad", "terrible", "awful", "rude", "slow", "dirty", "cold", "expensive",
                "never", "worst", "disappointing", "mauvais", "lent", "sale", "froid", "cher",
                "déçu", "decu", "déception", "horrible", "impoli", "attente", "jamais", "nul"]
    THEME_KEYWORDS = {
        "food": ["food", "dish", "plat", "pizza", "burger", "cuisine", "meal", "repas", "goût", "delicious", "délicieux", "froid", "cold"],
        "service": ["service", "staff", "waiter", "serveur", "serveuse", "personnel", "accueil", "rude", "impoli", "friendly"],
        "staff": ["staff", "waiter", "serveur", "personnel", "accueil", "équipe"],
        "price": ["price", "prix", "cher", "expensive", "value", "€", "addition", "bill"],
        "waiting": ["wait", "attente", "slow", "lent", "minutes", "long"],
        "cleanliness": ["dirty", "sale", "clean", "propre", "toilettes", "toilets"],
        "atmosphere": ["atmosphere", "ambiance", "music", "musique", "décor", "cosy", "noisy", "bruyant"],
        "menu": ["menu", "choice", "choix", "options", "vegetarian", "végétarien"],
    }

    def describe(self) -> str:
        return "Mock backend (keyword heuristics, used for automated tests only)"

    def sentiment(self, texts, batch_size=32, progress: ProgressFn = _noop):
        out = []
        for t in texts:
            low = t.lower()
            score = sum(w in low for w in self.POSITIVE) - sum(w in low for w in self.NEGATIVE)
            stars = 3 if score == 0 else (5 if score >= 2 else 4) if score > 0 else (1 if score <= -2 else 2)
            out.append((stars, 0.6))
        progress(1.0, "Sentiment")
        return out

    def themes(self, texts, labels, batch_size=16, progress: ProgressFn = _noop):
        out = []
        for t in texts:
            low = t.lower()
            scores = {}
            for label in labels:
                words = set(re.findall(r"[a-z]+", label.lower()))
                keywords = [k for key, kws in self.THEME_KEYWORDS.items() if key in words for k in kws]
                keywords += [w for w in words if len(w) > 3]
                scores[label] = 0.9 if any(k in low for k in keywords) else 0.1
            out.append(scores)
        progress(1.0, "Themes")
        return out

    def generate(self, conversations, max_new_tokens=350, batch_size=4):
        replies = []
        for conv in conversations:
            if "REPLY_TASK" in conv[-1]["content"]:
                replies.append("Thank you for taking the time to share your feedback. We are sorry "
                               "your visit did not meet your expectations and we will look into it. "
                               "Please contact us directly so we can make it right. The team")
            else:
                replies.append("### Strengths\n- Mock strength\n\n### Areas for improvement\n"
                               "- Mock weakness\n\n### 3 priority actions\n1. Mock action\n"
                               "2. Mock action\n3. Mock action")
        return replies


_BACKEND = None


def get_backend():
    """Return the shared backend (created once per session)."""
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = MockBackend() if os.environ.get("REVIEWPULSE_MOCK") == "1" else HFBackend()
    return _BACKEND
