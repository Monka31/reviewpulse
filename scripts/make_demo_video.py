"""Generate the narrated demo video automatically.

    python scripts/make_demo_video.py                      # ESSEC dataset, outputs/ReviewPulse_demo.mp4
    python scripts/make_demo_video.py --voice en-US-AndrewNeural   # another voice
    REVIEWPULSE_TTS=silent python scripts/make_demo_video.py   # silent test run

Needs: pip install playwright edge-tts (or kokoro), playwright install --with-deps chromium,
apt-get install espeak-ng ffmpeg. See documentation/USER_GUIDE.md, section "Demo video".
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reviewpulse.demo_video import make_demo_video  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=str(ROOT / "data" / "reviews_ESSEC_Cergy.csv"))
    p.add_argument("--name", default="ESSEC Business School · Cergy campus")
    p.add_argument("--type", default="School / University")
    p.add_argument("--out", default=str(ROOT / "outputs" / "ReviewPulse_demo.mp4"))
    p.add_argument("--engine", choices=["auto", "kokoro", "edge", "silent"], default=None)
    p.add_argument("--voice", default=None, help="edge-tts voice (en-US-AvaNeural, en-US-AndrewNeural...) or Kokoro voice (af_heart...)")
    p.add_argument("--no-subtitles", action="store_true")
    p.add_argument("--keep-frames", action="store_true")
    a = p.parse_args()
    make_demo_video(a.data, a.name, a.type, a.out, voice_engine=a.engine, voice=a.voice,
                    subtitles=not a.no_subtitles, keep_frames=a.keep_frames)


if __name__ == "__main__":
    main()
