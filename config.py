"""
Central configuration for the GTA VI Brainrot Automation Pipeline.
Reads from .env file, provides default values.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ── Directories ──────────────────────────────────────────────
RAW_DIR = ROOT / "data" / "raw"
CLIPS_DIR = ROOT / "data" / "clips"
OUTPUT_DIR = ROOT / "data" / "output"
CACHE_DIR = ROOT / "data" / "cache"

for d in [RAW_DIR, CLIPS_DIR, OUTPUT_DIR, CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Clip download settings ───────────────────────────────────
YTDL_SEARCH_QUERY = _env("YTDL_SEARCH_QUERY", "gta v funny moments gameplay 1080p")
YTDL_MAX_DOWNLOADS = int(_env("YTDL_MAX_DOWNLOADS", "2"))
YTDL_FORMAT = _env("YTDL_FORMAT", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]")

# ── Clip processing ──────────────────────────────────────────
SCENE_THRESHOLD = float(_env("SCENE_THRESHOLD", "0.3"))  # 0-1 sensitivity
CLIP_MIN_DURATION = float(_env("CLIP_LENGTH_MIN", "30"))
CLIP_MAX_DURATION = float(_env("CLIP_LENGTH_MAX", "55"))

# ── Groq LLM ─────────────────────────────────────────────────
GROQ_API_KEY = _env("GROQ_API_KEY")
GROQ_MODEL = _env("GROQ_MODEL", "llama-3.1-8b-instant")

# ── TTS ──────────────────────────────────────────────────────
TTS_VOICE = _env("EDGE_TTS_VOICE", "en-US-BrianMultilingualNeural")
TTS_RATE = _env("TTS_RATE", "-8%")

# ── Brainrot style ───────────────────────────────────────────
BRAINROT_STYLE = _env("BRAINROT_STYLE", "chaotic")

# ── Render settings ──────────────────────────────────────────
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
FPS = 60


# ── Cloudinary ───────────────────────────────────────────────
CLOUDINARY_CLOUD_NAME = _env("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = _env("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = _env("CLOUDINARY_API_SECRET")

# ── Instagram & Facebook Graph API ───────────────────────────
IG_ACCESS_TOKEN = _env("IG_ACCESS_TOKEN")
IG_ACCOUNT_ID = _env("IG_ACCOUNT_ID")
IG_API_VERSION = _env("IG_API_VERSION", "v20.0")
FB_PAGE_ID = _env("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = _env("FB_PAGE_ACCESS_TOKEN")

# ── Instagram ────────────────────────────────────────────────
IG_USERNAME = _env("IG_USERNAME")
IG_PASSWORD = _env("IG_PASSWORD")