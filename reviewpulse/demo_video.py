"""Fully automated demo video.

`make_demo_video()` produces a narrated MP4 of about five minutes, with no manual step:

1. it runs the analysis once to get the real figures (models stay loaded for the app);
2. it writes the narration from those figures (nothing is typed by hand);
3. it turns the narration into speech (edge-tts neural voices, or Kokoro from Hugging Face);
4. it drives a headless browser through GitHub, the Colab notebook and the app, taking
   screenshots frame by frame, so each shot lasts exactly as long as its sentence and the
   waiting time of the analysis is cut;
5. it assembles frames, voice and subtitles with ffmpeg.

Run it from the Colab notebook (section 8), or from the command line:
    python scripts/make_demo_video.py

Requirements (installed by the notebook cell): playwright + chromium, ffmpeg, and
edge-tts (default) or kokoro with espeak-ng. REVIEWPULSE_TTS=silent makes a silent test video.
"""

from __future__ import annotations

import asyncio
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/Monka31/reviewpulse"
COLAB_URL = "https://colab.research.google.com/github/Monka31/reviewpulse/blob/main/ReviewPulse.ipynb"
PAGES_URL = "https://monka31.github.io/reviewpulse/"

VIEW_W, VIEW_H, SCALE = 1440, 810, 4 / 3        # screenshots are 1920 x 1080
FPS = 15                                         # frame rate of animations (scroll, cursor)
SAMPLE_RATE = 24000
TARGET_SECONDS = (282, 300)                      # aim for 4:42 to 5:00 (allowed 4:30 to 5:30)

# Words the speech engine tends to mispronounce (used for the voice only, not the subtitles)
PRONUNCIATION = {
    "ESSEC": "Essec", "mDeBERTa": "M DeBERTa", "Qwen": "Kwen", "README": "read me", "GPU": "G P U",
}


def log(msg: str) -> None:
    print(f"[demo] {msg}", flush=True)


# =====================================================================================
# 1. Narration written from the real results
# =====================================================================================
def _pct(x) -> int:
    return int(round(float(x)))


def _clean_md(text: str) -> str:
    text = re.sub(r"\*\*|__|`", "", text)
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    return text[:1].lower() + text[1:] if text and not text[:2].isupper() else text


def demo_facts(result) -> dict:
    """Every figure the narration quotes, computed from the analysis."""
    from .dashboard import parse_diagnosis
    from .evaluation import evaluate

    s, df = result.stats, result.reviews
    f = {
        "name": result.business_name.split("·")[0].strip(),
        "avg": f"{s['avg_rating']:.2f}" if s.get("avg_rating") else f"{s['avg_predicted_stars']:.1f}",
        "n_total": s.get("n_rows_total", s["n_reviews"]),
        "n_written": s["n_reviews"],
        "avg_written": f"{s['avg_rating_written']:.2f}" if s.get("avg_rating_written") else None,
        "one_star": int((df["rating"] == 1).sum()),
        "pct_pos": _pct(s["pct_positive"]),
        "pct_neg": _pct(s["pct_negative"]),
        "unanswered": s.get("n_unanswered_negative"),
        "no_reply_at_all": bool(s.get("owner_answers_all_empty")),
    }

    # Trend per year, star-only ratings included
    ratings = pd.DataFrame(df.attrs.get("all_ratings", []), columns=["date", "rating"])
    ratings["date"] = pd.to_datetime(ratings["date"], errors="coerce")
    yearly = (ratings.dropna().assign(year=lambda d: d["date"].dt.year).groupby("year")
              .agg(avg=("rating", "mean"), n=("rating", "size"), neg=("rating", lambda r: 100 * (r <= 2).mean())))
    yearly = yearly[yearly["n"] >= 10]
    if len(yearly) >= 3:
        worst = yearly["avg"].idxmin()
        last = yearly.index.max()
        f["trend"] = {"worst_year": int(worst), "worst_avg": f"{yearly.loc[worst, 'avg']:.1f}",
                      "worst_neg": _pct(yearly.loc[worst, "neg"]), "last_year": int(last),
                      "last_avg": f"{yearly.loc[last, 'avg']:.1f}", "first_year": int(yearly.index.min()),
                      "first_avg": f"{yearly['avg'].iloc[0]:.1f}"}

    # Themes
    t = result.theme_table[result.theme_table["mentions"] > 0]
    if not t.empty:
        f["top_theme"] = t.sort_values("mentions", ascending=False).iloc[0]["theme"]
        enough = t[t["mentions"] >= max(2, t["mentions"].median())]
        fix = enough[enough["net_score"] < 0].sort_values(["mentions", "net_score"], ascending=[False, True])
        f["fix_theme"] = fix.iloc[0]["theme"] if not fix.empty else None
        f["weakest_theme"] = t.sort_values("net_score").iloc[0]["theme"]
        strong = t[(t["mentions"] >= 2) & (t["net_score"] > 0)].sort_values(["net_score", "mentions"], ascending=False)
        f["best_theme"] = strong.iloc[0]["theme"] if not strong.empty else None

    actions = parse_diagnosis(result.summary).get("actions", [])
    f["action"] = _clean_md(actions[0]) if actions else None

    ev = evaluate(df)
    if ev:
        f["acc"], f["base"] = _pct(100 * ev["accuracy_3_classes"]), _pct(100 * ev["baseline_majority_class"])
    return f


def build_script(f: dict) -> list[dict]:
    """The narration, one entry per shot. Texts are filled with the real figures."""
    name = f["name"]
    seg = []

    def add(key, text):
        seg.append({"key": key, "text": " ".join(text.split())})

    add("intro", "Every day, people leave reviews on Google. For a business, they say exactly what to fix. "
                 "But nobody has time to read hundreds of them. This is ReviewPulse, an AI assistant that "
                 "turns all the reviews of a business into a dashboard and clear actions, in about two minutes.")

    problem = (f"Take a place everyone at ESSEC knows: the Cergy campus. On Google, it has {f['avg']} stars out of five, "
               f"over {f['n_total']} ratings. That looks great. ")
    if f.get("avg_written"):
        problem += (f"But only {f['n_written']} people actually wrote something, and when they write, the average drops "
                    f"to {f['avg_written']}. {f['one_star']} of them gave a single star. ")
    problem += "The average hides what people are really saying."
    add("problem", problem)

    add("github", "The whole project is open source and on GitHub: the code, the anonymized data and the documentation. "
                  "The reviews were collected with Outscraper, and every reviewer's name was removed before the "
                  "analysis. The README explains the problem, the architecture and the results, and a single button "
                  "opens the project in Google Colab.")

    add("colab", "In Colab, you pick a free GPU and click Run all. The notebook downloads three open-source models from "
                 "Hugging Face. A multilingual BERT model reads the sentiment of each review. An mDeBERTa model sorts "
                 "the reviews into themes, with zero-shot learning, so it needs no training data. And Qwen 2.5, a small "
                 "language model, writes the diagnosis and the replies. The last cell starts the web app.")

    add("app", f"Here is the app. We drop the review file exported from Google, give the business a name and choose its "
               f"type: a school. Each type comes with its own themes, such as admissions, teaching or the campus, and "
               f"you can edit them. Then we click Analyze.")

    add("wait", "The analysis takes about a minute on a GPU, so let's skip ahead.")

    kpi = (f"The dashboard opens with the main figures: {f['avg']} stars over all ratings, {f['n_written']} written "
           f"reviews, {f['pct_neg']} percent of them negative")
    if f.get("unanswered") is not None:
        kpi += f", and {f['unanswered']} complaints that never got an answer."
        if f["no_reply_at_all"]:
            kpi += " In this export, not a single review received a reply."
    else:
        kpi += "."
    add("kpis", kpi)

    diag = ("Next comes the AI diagnosis. The language model does not read hundreds of reviews blindly: it receives "
            "the statistics and real excerpts, and writes strengths, weak points and three priority actions.")
    if f.get("action"):
        diag += f" Its first recommendation here: {f['action']}."
    add("diagnosis", diag)

    ins = f"The insights section shows how the written reviews split: {f['pct_pos']} percent positive and {f['pct_neg']} percent negative"
    ins += f", and which topics dominate. {f['top_theme'].capitalize()} comes up most often." if f.get("top_theme") else "."
    add("insights", ins)

    if f.get("trend"):
        tr = f["trend"]
        add("trend", f"Over time, the picture moves. The average was {tr['first_avg']} in {tr['first_year']}, fell to "
                     f"{tr['worst_avg']} in {tr['worst_year']}, with {tr['worst_neg']} percent of one and two-star "
                     f"ratings, and it is at {tr['last_avg']} in {tr['last_year']}. An owner sees at a glance whether "
                     f"things are getting better.")

    matrix = ("The priority matrix is the chart a manager needs most. It places each theme by how often it is "
              "mentioned, and by how people feel about it. ")
    if f.get("fix_theme"):
        matrix += f"{f['fix_theme'].capitalize()} sits in the Fix first corner: it comes up often, and mostly in negative reviews."
    elif f.get("weakest_theme"):
        matrix += f"No theme falls in the Fix first corner, and {f['weakest_theme']} is the one to watch."
    if f.get("best_theme"):
        matrix += f" On the bright side, {f['best_theme']} is a strength to promote."
    add("matrix", matrix)

    if f.get("acc") is not None:
        if f["acc"] >= f["base"]:
            trust = (f"Can we trust the AI? Every review comes with the stars its author gave, so the app checks itself. "
                     f"Here, the model agrees with customers {f['acc']} percent of the time, against {f['base']} percent "
                     f"for a naive guess.")
        else:
            trust = (f"Can we trust the AI? Every review comes with the stars its author gave, so the app checks itself. "
                     f"Here, the model agrees with customers {f['acc']} percent of the time, below the {f['base']} percent "
                     f"of a naive guess: short and mixed reviews are hard to read, and the app says so openly.")
        add("trust", trust)

    add("filters", "Filters let you dig deeper. Let's keep only the one and two-star reviews. The whole dashboard updates "
                   "instantly, without running the models again.")

    add("complaints", "Here are the complaints that never got an answer, newest first. For each one, ReviewPulse drafts "
                      "a public reply in the language of the review, which addresses what the person actually wrote. "
                      "The owner reads it, adjusts it and posts it.")

    add("assistant", "For any other review, the reply assistant writes a new draft on demand, in a few seconds.")

    add("table", "And at the bottom, every review sits in one table: written or star-only, answered or not, with the "
                 "AI's reading of each one, ready to search and export.")

    add("evaluation", "For the curious, the model evaluation compares the predicted stars with the real ones, class by "
                      "class, in a confusion matrix.")

    add("report", "Finally, each analysis can be exported as a static page and published on GitHub Pages, which gives "
                  "it a permanent link that anyone can open, without Colab.")

    add("outro", "Large chains pay consultants and software to read their reviews. Most independent restaurants, shops "
                 "and schools cannot. ReviewPulse gives them the same insight, for free, in minutes, with open models. "
                 "This video was generated automatically by the project itself: the clicks, the voice and the editing. "
                 "ReviewPulse: from hundreds of reviews to clear actions.")
    return seg


# =====================================================================================
# 2. Speech
# =====================================================================================
def _write_wav(path: Path, samples: np.ndarray) -> float:
    samples = np.clip(np.asarray(samples, dtype=np.float32), -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((samples * 32767).astype(np.int16).tobytes())
    return len(samples) / SAMPLE_RATE


def _wav_seconds(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def _speech_text(text: str) -> str:
    for word, say in PRONUNCIATION.items():
        text = re.sub(rf"\b{re.escape(word)}\b", say, text)
    return text


class Voice:
    """edge-tts (Microsoft neural voices) or Kokoro (Hugging Face); silence only for tests."""

    def __init__(self, engine: str | None = None, voice: str | None = None, speed: float = 1.0):
        self.engine = engine or os.environ.get("REVIEWPULSE_TTS", "auto")
        self.voice = voice
        self.speed = speed
        self._kokoro = None
        if self.engine == "auto":
            self.engine = "edge" if _importable("edge_tts") else "kokoro" if _importable("kokoro") else None
            if self.engine is None:
                raise RuntimeError("No speech engine: pip install edge-tts (or kokoro with espeak-ng).")
        log(f"voice engine: {self.engine}")

    def say(self, text: str, path: Path) -> float:
        try:
            return self._say(text, path)
        except Exception as exc:
            other = {"edge": "kokoro", "kokoro": "edge"}.get(self.engine)
            if other and _importable("edge_tts" if other == "edge" else "kokoro"):
                log(f"voice engine '{self.engine}' failed ({str(exc)[:80]}), switching to '{other}'")
                self.engine, self.voice = other, None
                return self._say(text, path)
            raise

    def _say(self, text: str, path: Path) -> float:
        spoken = _speech_text(text)
        if self.engine == "kokoro":
            if self._kokoro is None:
                from kokoro import KPipeline
                self._kokoro = KPipeline(lang_code="a")
            chunks = []
            for _, _, audio in self._kokoro(spoken, voice=self.voice or "af_heart", speed=self.speed):
                chunks.append(audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio))
            return _write_wav(path, np.concatenate(chunks))
        if self.engine == "edge":
            import edge_tts
            mp3 = path.with_suffix(".mp3")
            rate = f"{int(round((self.speed - 1) * 100)):+d}%"

            async def run():
                await edge_tts.Communicate(spoken, self.voice or "en-US-AvaNeural", rate=rate).save(str(mp3))

            _run_async(run())
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar",
                            str(SAMPLE_RATE), str(path)], check=True)
            return _wav_seconds(path)
        # silent test voice: about 2.6 words per second
        return _write_wav(path, np.zeros(int(SAMPLE_RATE * max(1.0, len(text.split()) / 2.6))))


def _importable(module: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(module) is not None


def _run_async(coro):
    """asyncio.run that also works inside Jupyter/Colab (which already runs an event loop)."""
    box = {}

    def target():
        box["v"] = asyncio.run(coro)

    t = threading.Thread(target=target)
    t.start()
    t.join()
    return box.get("v")


# =====================================================================================
# 3. Browser "camera": frames taken one by one, so time on screen is fully controlled
# =====================================================================================
OVERLAY_JS = r"""
(() => {
  if (window.__rp) return;
  const ensure = () => {
    if (document.getElementById('rp-cursor') || !document.body) return;
    const c = document.createElement('div');
    c.id = 'rp-cursor';
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2 L4 20 L9 15 L12.5 22 L15.5 20.6 L12 13.8 L19 13.8 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {position:'fixed', left:'-60px', top:'-60px', zIndex:2147483647, pointerEvents:'none',
                            transition:'none', filter:'drop-shadow(0 2px 3px rgba(0,0,0,.35))'});
    document.body.appendChild(c);
    const h = document.createElement('div');
    h.id = 'rp-highlight';
    Object.assign(h.style, {position:'fixed', zIndex:2147483646, pointerEvents:'none', border:'3px solid #00A0E0',
                            borderRadius:'14px', boxShadow:'0 0 0 6px rgba(0,160,224,.18)', display:'none'});
    document.body.appendChild(h);
    const r = document.createElement('div');
    r.id = 'rp-ripple';
    Object.assign(r.style, {position:'fixed', zIndex:2147483645, pointerEvents:'none', width:'44px', height:'44px',
                            borderRadius:'50%', background:'rgba(0,160,224,.35)', display:'none', transform:'translate(-50%,-50%)'});
    document.body.appendChild(r);
  };
  window.__rp = {
    cursor: (x, y) => { ensure(); const c = document.getElementById('rp-cursor'); c.style.left = (x - 4) + 'px'; c.style.top = (y - 2) + 'px'; },
    ripple: (x, y, on) => { ensure(); const r = document.getElementById('rp-ripple'); r.style.left = x + 'px'; r.style.top = y + 'px'; r.style.display = on ? 'block' : 'none'; },
    highlight: (rect) => { ensure(); const h = document.getElementById('rp-highlight');
      if (!rect) { h.style.display = 'none'; return; }
      Object.assign(h.style, {display:'block', left:(rect.x - 8) + 'px', top:(rect.y - 8) + 'px', width:(rect.w + 16) + 'px', height:(rect.h + 16) + 'px'}); },
  };
  document.addEventListener('DOMContentLoaded', ensure);
})();
"""


class Camera:
    def __init__(self, page, frames_dir: Path):
        self.page = page
        self.dir = frames_dir
        self.frames: list[list] = []      # [path, duration]
        self.cursor = (VIEW_W * 0.6, VIEW_H * 0.6)
        self.n = 0

    @property
    def elapsed(self) -> float:
        return sum(d for _, d in self.frames)

    def shot(self, duration: float = 1 / FPS) -> None:
        self.n += 1
        path = self.dir / f"f{self.n:05d}.jpg"
        try:
            self.page.evaluate("([x, y]) => window.__rp && window.__rp.cursor(x, y)", list(self.cursor))
        except Exception:
            pass
        self.page.screenshot(path=str(path), type="jpeg", quality=90, animations="disabled")
        self.frames.append([path, duration])

    def hold(self, seconds: float) -> None:
        if seconds <= 0:
            return
        if self.frames:
            self.frames[-1][1] += seconds
        else:
            self.shot(seconds)

    def pause(self, seconds: float) -> None:
        """A fresh frame that stays on screen (content may have changed)."""
        self.shot(max(seconds, 1 / FPS))

    # ---- motion -------------------------------------------------------------------
    def move_to(self, target, seconds: float = 0.7) -> tuple[float, float]:
        box = target.bounding_box() if not isinstance(target, tuple) else None
        x, y = (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2) if box else target
        x0, y0 = self.cursor
        steps = max(2, int(seconds * FPS))
        for i in range(1, steps + 1):
            t = i / steps
            e = t * t * (3 - 2 * t)
            self.cursor = (x0 + (x - x0) * e, y0 + (y - y0) * e)
            self.shot()
        return x, y

    def click(self, locator, seconds: float = 0.7) -> None:
        locator.scroll_into_view_if_needed()
        x, y = self.move_to(locator, seconds)
        self.page.evaluate("([x, y]) => window.__rp.ripple(x, y, true)", [x, y])
        self.shot(0.18)
        self.page.evaluate("() => window.__rp.ripple(0, 0, false)")
        locator.click()
        self.shot(0.25)

    def type(self, locator, text: str) -> None:
        self.click(locator, 0.5)
        locator.fill("")
        for i, ch in enumerate(text):
            self.page.keyboard.type(ch)
            if i % 2 == 1 or i == len(text) - 1:
                self.shot()

    def scroll_to(self, y_target: float, seconds: float = 1.6) -> None:
        y0 = self.page.evaluate("() => window.scrollY")
        max_y = self.page.evaluate("() => document.documentElement.scrollHeight - window.innerHeight")
        y1 = max(0, min(y_target, max_y))
        steps = max(2, int(seconds * FPS))
        for i in range(1, steps + 1):
            t = i / steps
            e = t * t * (3 - 2 * t)
            self.page.evaluate("(y) => window.scrollTo(0, y)", y0 + (y1 - y0) * e)
            self.shot()

    def scroll_to_el(self, locator, offset: float = 90, seconds: float = 1.6) -> None:
        y = self.page.evaluate("(el) => el.getBoundingClientRect().top + window.scrollY", locator.element_handle())
        self.scroll_to(y - offset, seconds)

    def highlight(self, locator=None, pad: int = 0) -> None:
        if locator is None:
            self.page.evaluate("() => window.__rp && window.__rp.highlight(null)")
            return
        b = locator.bounding_box()
        if b:
            self.page.evaluate("(r) => window.__rp.highlight(r)",
                               {"x": b["x"] - pad, "y": b["y"] - pad, "w": b["width"] + 2 * pad, "h": b["height"] + 2 * pad})


# =====================================================================================
# 4. Static cards (title, the problem, the end)
# =====================================================================================
CARD_CSS = """
body{margin:0;width:1440px;height:810px;display:flex;align-items:center;justify-content:center;
background:#F6F7F9;font-family:Inter,system-ui,sans-serif;color:#101828;overflow:hidden}
.t{font-family:'Plus Jakarta Sans',Inter,sans-serif;font-weight:800;letter-spacing:-1px}
.logo{width:64px;height:64px;border-radius:16px;background:#00A0E0;display:flex;align-items:center;justify-content:center}
.muted{color:#5B6474}
"""
LOGO_SVG = ('<div class="logo"><svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" '
            'stroke-linecap="round" stroke-linejoin="round"><polyline points="2 12 7 12 10 5 14 19 17 12 22 12"/></svg></div>')


def _card(body: str) -> str:
    from .dashboard import FONTS_LINK
    return f"<!doctype html><html><head><meta charset='utf-8'>{FONTS_LINK}<style>{CARD_CSS}</style></head><body>{body}</body></html>"


def title_card() -> str:
    return _card(f"""<div style="text-align:center">
<div style="display:flex;justify-content:center;margin-bottom:26px">{LOGO_SVG}</div>
<div class="t" style="font-size:88px">ReviewPulse</div>
<div style="font-size:30px;margin-top:10px" class="muted">From hundreds of reviews to clear actions</div>
<div style="margin-top:60px;font-size:18px" class="muted">Advanced AI Algorithms · ESSEC Business School · 2026</div></div>""")


def problem_card(result, facts: dict) -> str:
    df = result.reviews
    neg = df[(df["rating"] <= 2)].head(2)
    pos = df[(df["rating"] >= 4) & (df["text"].str.len().between(20, 160))].head(2)
    quotes = []
    for _, r in pd.concat([pos.head(1), neg.head(2), pos.iloc[1:2]]).iterrows():
        text = " ".join(r["text"].split())
        text = text if len(text) <= 150 else text[:147].rsplit(" ", 1)[0] + "…"
        stars = int(r["rating"])
        quotes.append(f'<div style="background:#fff;border:1px solid #E4E7EC;border-radius:14px;padding:14px 18px">'
                      f'<div style="color:#E8590C;letter-spacing:2px">{"★" * stars}<span style="color:#D0D5DD">{"★" * (5 - stars)}</span></div>'
                      f'<div style="font-size:16px;margin-top:4px">{html.escape(text)}</div></div>')
    written = (f'<div style="font-size:22px;margin-top:22px">Written reviews only: <b style="color:#C2410C">'
               f'{facts["avg_written"]} / 5</b> · {facts["one_star"]} one-star reviews</div>') if facts.get("avg_written") else ""
    return _card(f"""<div style="display:flex;gap:56px;align-items:center;padding:0 80px">
<div style="flex:1"><div class="muted" style="font-size:18px;font-weight:600;text-transform:uppercase;letter-spacing:1px">Google Maps</div>
<div class="t" style="font-size:44px;margin:6px 0 10px">{html.escape(result.business_name.split('·')[0].strip())}</div>
<div style="font-size:64px;font-weight:800" class="t">{facts['avg']} <span style="font-size:30px" class="muted">/ 5 · {facts['n_total']} ratings</span></div>
{written}</div>
<div style="flex:1;display:flex;flex-direction:column;gap:12px">{''.join(quotes)}</div></div>""")


def end_card() -> str:
    return _card(f"""<div style="text-align:center">
<div style="display:flex;justify-content:center;margin-bottom:22px">{LOGO_SVG}</div>
<div class="t" style="font-size:72px">ReviewPulse</div>
<div style="font-size:26px;margin-top:8px" class="muted">From hundreds of reviews to clear actions</div>
<div style="margin-top:46px;font-size:22px;line-height:1.9">
<div>Code, data and user guide: <b>github.com/Monka31/reviewpulse</b></div>
<div>Published reports: <b>monka31.github.io/reviewpulse</b></div></div>
<div style="margin-top:40px;font-size:16px" class="muted">Narration, browsing and editing generated automatically by the project.</div></div>""")


def notebook_page() -> str:
    """Readable render of our own notebook, used only when Colab cannot be opened headless."""
    import nbformat
    nb = nbformat.read(str(ROOT / "ReviewPulse.ipynb"), 4)
    import markdown as md
    cells = []
    for c in nb.cells:
        if c.cell_type == "markdown":
            cells.append(f'<div style="padding:6px 18px">{md.markdown(c.source)}</div>')
        else:
            cells.append('<div style="display:flex;gap:10px;margin:8px 0"><div style="width:30px;height:30px;border-radius:50%;'
                         'background:#E8EAED;flex:none;margin-top:6px"></div><pre style="flex:1;margin:0;background:#F7F7F7;'
                         'border:1px solid #E0E0E0;border-radius:8px;padding:12px;font:13px/1.45 Menlo,Consolas,monospace;'
                         f'white-space:pre-wrap">{html.escape(c.source)}</pre></div>')
    return _card("").replace("<body></body>", f"""<body style="display:block;height:auto;overflow:auto;background:#fff">
<div style="background:#F8F9FA;border-bottom:1px solid #E0E0E0;padding:12px 24px;font:16px Inter,sans-serif">
<b>ReviewPulse.ipynb</b> <span class="muted">· Runtime: T4 GPU · Run all</span></div>
<div style="max-width:1100px;margin:0 auto;padding:16px 24px 80px;font-size:15px">{''.join(cells)}</div></body>""")


# =====================================================================================
# 5. The film
# =====================================================================================
def _record(segments, audio, app_url: str, result, frames_dir: Path, pad: float, report_path: Path) -> list[dict]:
    from playwright.sync_api import sync_playwright

    timeline = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--hide-scrollbars", "--force-color-profile=srgb"])
        ctx = browser.new_context(viewport={"width": VIEW_W, "height": VIEW_H}, device_scale_factor=SCALE,
                                  locale="en-US", color_scheme="light")
        ctx.add_init_script(OVERLAY_JS)
        page = ctx.new_page()
        cam = Camera(page, frames_dir)
        by_key = {s["key"]: s for s in segments}

        def segment(key, action):
            if key not in by_key:
                return
            start = cam.elapsed
            log(f"recording: {key}")
            try:
                action()
            except Exception as exc:  # a failed shot must not kill the whole film
                log(f"  warning in '{key}': {str(exc).splitlines()[0][:160]}")
                if not cam.frames:
                    cam.shot()
            target = audio[key] + pad
            cam.hold(target - (cam.elapsed - start))
            timeline.append({"key": key, "start": start, "end": cam.elapsed})

        def html_page(content, cursor=False):
            page.set_content(content, wait_until="networkidle")
            page.wait_for_timeout(300)
            if not cursor:
                cam.cursor = (-100, -100)

        # ---- 1. title and problem cards
        segment("intro", lambda: (html_page(title_card()), cam.shot()))
        segment("problem", lambda: (html_page(problem_card(result, demo_facts(result))), cam.shot()))

        # ---- 2. GitHub
        def github():
            cam.cursor = (VIEW_W * 0.55, VIEW_H * 0.5)
            page.goto(REPO_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            cam.shot(1.2)
            readme = page.locator("article.markdown-body").first
            if readme.count():
                cam.scroll_to_el(readme, 70, 2.0)
                cam.pause(1.5)
                cam.scroll_to(page.evaluate("() => window.scrollY") + 650, 3.0)
                cam.pause(1.2)
                badge = page.locator("article.markdown-body img[alt='Open In Colab']").first
                if badge.count():
                    cam.scroll_to_el(badge, 260, 1.5)
                    cam.highlight(badge, 4)
                    cam.move_to(badge, 0.8)
                    cam.pause(1.0)
                    cam.highlight(None)
        segment("github", github)

        # ---- 3. Colab (falls back to a render of the notebook if Colab needs a sign-in)
        def colab():
            shown = False
            try:
                page.goto(COLAB_URL, wait_until="domcontentloaded", timeout=45000)
                page.get_by_text("Check the GPU").first.wait_for(timeout=30000)
                page.wait_for_timeout(2000)
                shown = True
            except Exception:
                log("  Colab not readable without sign-in: showing the notebook content instead")
                html_page(notebook_page(), cursor=True)
                cam.cursor = (VIEW_W * 0.55, VIEW_H * 0.5)
            cam.shot(1.0)
            for _ in range(3):
                page.mouse.wheel(0, 0)
                if shown:
                    page.mouse.move(VIEW_W / 2, VIEW_H / 2)
                    for _ in range(int(2.2 * FPS)):
                        page.mouse.wheel(0, 18)
                        cam.shot()
                else:
                    cam.scroll_to(page.evaluate("() => window.scrollY") + 520, 2.2)
                cam.pause(0.9)
        segment("colab", colab)

        # ---- 4. The app: upload, settings, analyze
        def app_setup():
            page.goto(app_url, wait_until="domcontentloaded", timeout=60000)
            page.get_by_text("New analysis").first.wait_for(timeout=60000)
            page.wait_for_timeout(1500)
            cam.shot(1.0)
            upload = page.locator("input[type=file]").first
            target = page.get_by_text("Review file (Outscraper Excel or CSV)").first
            cam.move_to(target, 0.8)
            upload.set_input_files(str(result.reviews.attrs.get("source_path")))
            page.wait_for_timeout(1500)
            cam.pause(0.8)
            cam.type(page.locator("label:has-text('Business name') textarea").first, result.business_name)
            cam.pause(0.4)
            cam.click(page.get_by_label(result.business_type), 0.7)
            cam.pause(0.8)
            cam.highlight(page.locator("label:has-text('Themes to detect') textarea").first, 4)
            cam.pause(1.6)
            cam.highlight(None)
            cam.click(page.get_by_role("button", name="Analyze reviews"), 0.8)
            page.wait_for_timeout(1200)
            cam.pause(0.8)
        segment("app", app_setup)

        def wait():
            cam.pause(1.2)
            log("  waiting for the analysis (not recorded)")
            page.get_by_text("Priority matrix").first.wait_for(timeout=20 * 60 * 1000)
            page.wait_for_timeout(1500)
            cam.scroll_to(0, 0.3)
            cam.pause(0.5)
        segment("wait", wait)

        dash_top = lambda sel: page.locator(sel).first  # noqa: E731

        def kpis():
            cam.scroll_to_el(dash_top(".rp .kpis"), 150, 1.2)
            cam.highlight(dash_top(".rp .kpis"), 2)
            cam.pause(2.5)
            cam.highlight(None)
        segment("kpis", kpis)

        def diagnosis():
            card = page.locator(".rp .card").filter(has_text="AI diagnosis").first
            cam.scroll_to_el(card, 110, 1.4)
            cam.highlight(card, 2)
            cam.pause(1.5)
            actions = card.locator("ol").first
            if actions.count():
                cam.move_to(actions, 0.9)
        segment("diagnosis", lambda: (diagnosis(), cam.highlight(None)))

        def insights():
            cam.scroll_to_el(page.get_by_text("Insights", exact=True).first, 80, 1.6)
            cam.pause(1.0)
            cam.move_to(page.locator(".rp .donut svg").first, 0.8)
            cam.pause(1.5)
            cam.move_to(page.locator(".rp .donut svg").nth(1), 0.8)
        segment("insights", insights)

        def trend():
            card = page.locator(".rp .card").filter(has_text="Rating and complaints over time").first
            cam.scroll_to_el(card, 90, 1.4)
            cam.highlight(card, 2)
            cam.pause(1.2)
            cam.move_to(card.locator("svg").first, 1.0)
        segment("trend", lambda: (trend(), cam.highlight(None)))

        def matrix():
            card = page.locator(".rp .card").filter(has_text="Priority matrix").first
            cam.scroll_to_el(card, 80, 1.5)
            cam.highlight(card, 2)
            cam.pause(1.5)
            fix = card.get_by_text("Fix first").first
            if fix.count():
                cam.move_to(fix, 1.0)
        segment("matrix", lambda: (matrix(), cam.highlight(None)))

        def trust():
            card = page.locator(".rp .card").filter(has_text="Star ratings").last
            cam.scroll_to_el(card, 100, 1.5)
            rel = card.get_by_text("AI reliability on these reviews").first
            if rel.count():
                cam.highlight(rel.locator("xpath=.."), 6)
                cam.move_to(rel, 0.9)
        segment("trust", lambda: (trust(), cam.highlight(None)))

        def filters():
            cam.scroll_to(0, 1.4)
            stars = page.get_by_role("combobox", name="Stars")
            cam.click(stars, 0.8)
            page.wait_for_timeout(500)
            cam.pause(0.6)
            cam.click(page.get_by_role("option", name="1 to 2 stars"), 0.7)
            page.get_by_text("Filtered view").first.wait_for(timeout=60000)
            page.wait_for_timeout(800)
            cam.pause(1.0)
            cam.scroll_to_el(dash_top(".rp .kpis"), 160, 1.0)
            cam.highlight(dash_top(".rp .kpis"), 2)
            cam.pause(1.4)
        segment("filters", lambda: (filters(), cam.highlight(None)))

        def complaints():
            card = page.locator(".rp .card").filter(has_text="Complaints without an answer").first
            cam.scroll_to_el(card, 80, 1.8)
            cam.pause(1.2)
            reply = card.locator(".reply").first
            if reply.count():
                cam.scroll_to_el(reply, 260, 1.2)
                cam.highlight(reply, 4)
                cam.move_to(reply, 0.8)
                cam.pause(1.5)
        segment("complaints", lambda: (complaints(), cam.highlight(None)))

        def assistant():
            btn = page.get_by_role("button", name="Draft a reply")
            cam.scroll_to_el(page.get_by_text("Reply assistant").first, 60, 1.6)
            cam.pause(0.8)
            box = page.locator("label:has-text('Suggested reply (editable)') textarea").first
            before = box.input_value()
            cam.click(btn, 0.8)
            for _ in range(600):  # up to ~2 minutes, not recorded
                page.wait_for_timeout(200)
                value = box.input_value()
                if value and value != before:
                    break
            page.wait_for_timeout(400)
            cam.highlight(box, 4)
            cam.pause(1.4)
        segment("assistant", lambda: (assistant(), cam.highlight(None)))

        def table():
            heading = page.locator(".rp h2", has_text="All reviews").first
            cam.scroll_to_el(heading, 80, 1.8)
            cam.pause(1.0)
            scroller = heading.locator("xpath=ancestor::div[contains(@class,'card')]//div[contains(@style,'overflow:auto')]").first
            if scroller.count():
                cam.move_to(scroller, 0.6)
                for i in range(int(2.4 * FPS)):
                    scroller.evaluate("(el, y) => el.scrollTop = y", i * 9)
                    cam.shot()
        segment("table", table)

        def evaluation():
            acc = page.get_by_text("Model evaluation", exact=True).first
            cam.scroll_to_el(acc, 120, 1.4)
            cam.click(acc, 0.7)
            page.wait_for_timeout(2500)
            cam.pause(0.5)
            cam.scroll_to(page.evaluate("() => window.scrollY") + 420, 1.6)
            cam.pause(1.0)
        segment("evaluation", evaluation)

        def report():
            page.goto(report_path.as_uri(), wait_until="networkidle")
            page.wait_for_timeout(800)
            cam.shot(1.2)
            cam.scroll_to(900, 3.0)
            cam.pause(0.8)
            cam.scroll_to(2200, 3.0)
        segment("report", report)

        segment("outro", lambda: (html_page(end_card()), cam.shot()))

        frames = cam.frames
        browser.close()
    return timeline, frames


# =====================================================================================
# 6. Assembly
# =====================================================================================
def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def _subtitles(segments, audio, timeline, lead: float) -> str:
    lines, n = [], 0
    for seg in segments:
        span = next((t for t in timeline if t["key"] == seg["key"]), None)
        if not span:
            continue
        sentences = [x for x in re.split(r"(?<=[.!?:])\s+", seg["text"]) if x]
        # long sentences are split in two to stay readable
        parts = []
        for snt in sentences:
            words = snt.split()
            if len(words) > 18:
                cut = len(words) // 2
                parts += [" ".join(words[:cut]), " ".join(words[cut:])]
            else:
                parts.append(snt)
        total_chars = sum(len(x) for x in parts) or 1
        t = span["start"] + lead
        for part in parts:
            dur = audio[seg["key"]] * len(part) / total_chars
            n += 1
            lines.append(f"{n}\n{_srt_time(t)} --> {_srt_time(t + dur)}\n{part}\n")
            t += dur
    return "\n".join(lines)


def _assemble(frames, timeline, audio_files, audio, segments, out_path: Path, work: Path,
              lead: float, subtitles: bool) -> Path:
    total = sum(d for _, d in frames)
    # concat list for the frames
    lst = work / "frames.txt"
    with open(lst, "w") as fh:
        for path, dur in frames:
            fh.write(f"file '{path}'\nduration {dur:.4f}\n")
        fh.write(f"file '{frames[-1][0]}'\n")
    # narration track aligned on the timeline
    track = np.zeros(int((total + 1) * SAMPLE_RATE), dtype=np.int16)
    for span in timeline:
        wav = audio_files.get(span["key"])
        if not wav:
            continue
        with wave.open(str(wav)) as w:
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        i = int((span["start"] + lead) * SAMPLE_RATE)
        track[i:i + len(data)] = data[: max(0, len(track) - i)]
    narration = work / "narration.wav"
    with wave.open(str(narration), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(track.tobytes())

    vf = "fps=30,format=yuv420p"
    if subtitles:
        srt = work / "subtitles.srt"
        srt.write_text(_subtitles(segments, audio, timeline, lead), encoding="utf-8")
        style = ("FontName=DejaVu Sans,FontSize=15,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,"
                 "BorderStyle=4,Outline=0,Shadow=0,MarginV=22,Alignment=2")
        vf_sub = vf + f",subtitles={srt.as_posix()}:force_style='{style}'"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(narration),
           "-vf", vf_sub if subtitles else vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out_path)]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        if not subtitles:
            raise
        log("subtitles could not be burned in (ffmpeg without libass): rendering without them")
        cmd[cmd.index(vf_sub)] = vf
        subprocess.run(cmd, check=True)
    return out_path


# =====================================================================================
# 7. Entry point
# =====================================================================================
def make_demo_video(data_file: str | Path = ROOT / "data" / "reviews_ESSEC_Cergy.csv",
                    business_name: str = "ESSEC Business School · Cergy campus",
                    business_type: str = "School / University",
                    out_path: str | Path = ROOT / "outputs" / "ReviewPulse_demo.mp4",
                    voice_engine: str | None = None, voice: str | None = None,
                    subtitles: bool = True, keep_frames: bool = False) -> Path:
    """Build the whole demo video and return its path."""
    import reviewpulse as rp
    from app import build_app, THEME, APP_CSS
    from .dashboard import FONTS_LINK

    t0 = time.time()
    data_file = Path(data_file).resolve()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="rp_demo_"))
    (work / "frames").mkdir()
    (work / "audio").mkdir()

    # 1. the real figures (same settings as the app's defaults, so both runs give the same text)
    log("running the analysis to write the narration")
    result = rp.run_pipeline(data_file, business_name=business_name, business_type=business_type,
                             max_reviews=rp.config.MAX_REVIEWS_DEFAULT, language="English", n_replies=5)
    result.reviews.attrs["source_path"] = str(data_file)
    facts = demo_facts(result)
    (work / "facts.json").write_text(json.dumps(facts, indent=2, default=str))
    segments = build_script(facts)
    words = sum(len(s["text"].split()) for s in segments)
    log(f"narration: {len(segments)} shots, {words} words")

    # 2. the voice, tuned so the film lands between 4:42 and 5:00
    speaker = Voice(voice_engine, voice)
    audio, files = {}, {}
    for s in segments:
        path = work / "audio" / f"{s['key']}.wav"
        audio[s["key"]] = speaker.say(s["text"], path)
        files[s["key"]] = path
    spoken = sum(audio.values())
    if spoken > TARGET_SECONDS[1] - 0.6 * len(segments) and speaker.engine != "silent":
        speaker.speed = min(1.2, spoken / (TARGET_SECONDS[1] - 0.8 * len(segments)))
        log(f"narration too long ({spoken:.0f}s): speeding the voice up to x{speaker.speed:.2f}")
        for s in segments:
            audio[s["key"]] = speaker.say(s["text"], files[s["key"]])
        spoken = sum(audio.values())
    # breathing room after each shot, plus the time taken by on-screen motion
    pad = min(3.0, max(0.7, (sum(TARGET_SECONDS) / 2 - spoken - 25) / len(segments)))
    log(f"voice: {spoken:.0f}s, pause after each shot: {pad:.1f}s")

    # 3. the static report shown at the end
    report_path = rp.export_report(result, out_dir=work / "site", max_replies=5)

    # 4. the app, on a local port, sharing the models already in memory
    demo = build_app()
    demo.queue().launch(prevent_thread_lock=True, server_port=7899, share=False, quiet=True, inline=False,
                        theme=THEME, css=APP_CSS, head=FONTS_LINK, allowed_paths=[str(data_file.parent)])
    app_url = "http://127.0.0.1:7899/"

    # 5. the film (in a thread: Playwright's sync API cannot run inside Jupyter's event loop)
    box = {}

    def film():
        try:
            box["v"] = _record(segments, audio, app_url, result, work / "frames", pad, report_path)
        except Exception as exc:
            box["e"] = exc

    th = threading.Thread(target=film)
    th.start()
    th.join()
    try:
        demo.close()
    except Exception:
        pass
    if "e" in box:
        raise box["e"]
    timeline, frames = box["v"]

    # 6. assembly
    lead = 0.35
    log("assembling the video")
    _assemble(frames, timeline, files, audio, segments, out_path, work, lead, subtitles)
    total = timeline[-1]["end"]
    log(f"done: {out_path} · {int(total // 60)}:{int(total % 60):02d} · built in {(time.time() - t0) / 60:.1f} min")
    if not (270 <= total <= 330):
        log("WARNING: the video is outside 4:30 to 5:30")
    if keep_frames:
        log(f"frames kept in {work}")
    else:
        shutil.rmtree(work / "frames", ignore_errors=True)
    return out_path
