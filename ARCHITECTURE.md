# GTA V Brainrot Shorts Pipeline — Architecture & Implementation Guide

## Overview

This project is a fully automated Python pipeline that creates viral **brainrot-style GTA V Instagram Reels & Facebook Page Reels**. It downloads gameplay clips, extracts short segments via scene detection, generates a funny hook-first script using Groq LLM, synthesizes a voiceover with Edge TTS, and renders a 9:16 vertical video with kinetic word-by-word captions.

The pipeline automatically uploads the rendered video to **Cloudinary** for temporary hosting, then uses the **Meta Graph API** to publish it to **Instagram Reels** and optionally to a **Facebook Page** (using the same hosted URL to avoid duplicate uploads). After successful publication, it automatically deletes the video from Cloudinary.

---

## Project Structure

```
GTA_VI_Automation/
├── config.py                # Central configuration (paths, API keys, settings)
├── analytics_optimizer.py   # Step 0: Meta Graph API retention & style intelligence engine
├── download_clips.py        # Step 1: Download GTA V gameplay via yt-dlp (403 bypass)
├── process_clips.py         # Step 2: Extract short clips & anti-duplication rotation tracking
├── generate_script.py       # Step 3: Generate brainrot script via Groq LLM (adaptive word counts)
├── generate_voiceover.py    # Step 4: Synthesize voiceover via Edge TTS (clean plain text)
├── render_short.py          # Step 5: Render 9:16 video with kinetic captions via FFmpeg
├── run_pipeline.py          # Orchestrator: runs closed-loop self-optimizing pipeline
├── upload_instagram.py      # Automated Instagram Reels & Facebook Page Reels upload
├── .env                     # Local config (API keys, credentials) — NEVER COMMIT
├── .env.example             # Template for .env
├── .gitignore               # Ignore .env, __pycache__, data/output/, data/raw/
├── requirements.txt         # Python dependencies
├── ARCHITECTURE.md          # This file
├── README.md                # Quick-start guide
└── data/
    ├── clips/               # Committed gameplay clips (tracked in git)
    ├── raw/                 # Downloaded raw videos (gitignored)
    ├── output/              # Generated voiceover.mp3, final_short.mp4 (gitignored)
    └── cache/               # Session files, used_clips.json, analytics_intelligence.json
```

---

## Data Flow

```
Meta Graph API (Instagram & Facebook Insights)
    │
    ▼ [analytics_optimizer.py]
data/cache/analytics_intelligence.json (retention status, style weights, word count targets)
    │
    ├────────────────────────────────────────┐
    ▼                                        ▼
Probabilistic Style Selection            Adaptive Target Word Counts
    │                                        │
    ▼                                        ▼
YouTube (yt-dlp 403 bypass)             generate_script.py (Groq LLM)
    │                                        │
    ▼                                        ▼
data/clips/ ──► [Anti-Duplication] ──► Voiceover & Kinetic Render ──► Cloudinary ──► Meta Graph Publish
```
         ├──► upload_instagram.py (Instagram Reels via Graph API)
         ├──► upload_instagram.py (Facebook Page Reels via Graph API)
         │
         ▼ [Finally]
    Cloudinary Asset Cleaned Up
```

---

## File-by-File Breakdown

### 1. `config.py` — Central Configuration

**Purpose:** Reads `.env` file, provides defaults for all configurable settings.

**Key variables:**

| Variable | Default | Description |
|---|---|---|
| `RAW_DIR` | `data/raw/` | Downloaded raw videos |
| `CLIPS_DIR` | `data/clips/` | Extracted short clips |
| `OUTPUT_DIR` | `data/output/` | Generated voiceover + rendered video |
| `CACHE_DIR` | `data/cache/` | Session files, archives |
| `YTDL_SEARCH_QUERY` | `"gta v funny moments gameplay 1080p"` | YouTube search query |
| `YTDL_MAX_DOWNLOADS` | `2` | Max videos per download run |
| `YTDL_FORMAT` | `bestvideo[height<=1080][ext=mp4]+bestaudio...` | yt-dlp format string |
| `SCENE_THRESHOLD` | `0.3` | FFmpeg scene detection sensitivity |
| `CLIP_MIN_DURATION` | `15` | Minimum clip length in seconds |
| `CLIP_MAX_DURATION` | `40` | Maximum clip length in seconds |
| `GROQ_API_KEY` | from `.env` | Groq LLM API key |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq model name |
| `TTS_VOICE` | `en-US-BrianMultilingualNeural` | Default Edge TTS voice |
| `CLOUDINARY_CLOUD_NAME` | from `.env` | Cloudinary Cloud Name |
| `CLOUDINARY_API_KEY` | from `.env` | Cloudinary API Key |
| `CLOUDINARY_API_SECRET` | from `.env` | Cloudinary API Secret |
| `IG_ACCESS_TOKEN` | from `.env` | Meta Graph Access Token |
| `IG_ACCOUNT_ID` | from `.env` | Instagram Business Account ID |
| `FB_PAGE_ID` | from `.env` | Facebook Page ID |
| `FB_PAGE_ACCESS_TOKEN` | from `.env` | Facebook Page Access Token |

---

### 2. `download_clips.py` — Gameplay Downloader

**Purpose:** Downloads fresh gameplay videos using yt-dlp.

**Behavior:**
- Runs `yt-dlp` in a subprocess with search query and limits
- Saves to `data/raw/`
- Tracks downloaded video IDs in `data/cache/archive.txt` to avoid duplicates
- Has 120s timeout and graceful exception handling for runner blocks

---

### 3. `process_clips.py` — Scene Boundary Splitter

**Purpose:** Identifies scene transitions in raw videos and splits them into short clips.

**Behavior:**
- Gets video duration using `ffprobe`
- Detects transitions using FFmpeg's `select='gt(scene,0.3)'` filter
- Extracts 15-40s segments from between transitions
- Cleans up raw video files after extraction
- Keeps only the top 10 largest clips in `data/clips/` (cleans up short/empty files)

---

### 4. `generate_script.py` — Script Generator

**Purpose:** Generates a viral brainrot script.

**Behavior:**
- Calls Groq API (`openai/gpt-oss-20b` model) with system prompt
- Rotates between 12 distinct content formats (Facts, Advice, Tiers, POV, Speaker, Lore, etc.)
- Strips out any emojis from narration for TTS compatibility
- Performs SFW brand safety scanning using a forbidden terms list
- Identifies and outputs a clickbait title and 2-3 ALL CAPS keywords for subtitles
- Concludes with a definitive, punchy punchline that ends the video decisively

---

### 5. `generate_voiceover.py` — Edge TTS Engine

**Purpose:** Synthesizes voiceover audio and returns sentence timestamps.

**Behavior:**
- Normalizes text casing (lowercases ALL CAPS words) so Edge TTS does not spell them out letter-by-letter
- Streams TTS chunk-by-chunk using `edge_tts.Communicate`
- Captures `SentenceBoundary` events to record offsets and durations in milliseconds
- Returns total duration and timing data dictionary for subtitles

---

### 6. `render_short.py` — FFmpeg Video Composer

**Purpose:** Renders the 9:16 short with kinetic subtitles.

**Composition details:**
- Up-scales central region of input video (sharp Lanczos scale + unsharp filter)
- Overlays it on top of a blurred, up-scaled copy of the same clip to populate 9:16 layout
- Generates ASS captions synced to the TTS sentence timestamps
- Captions have scale pop-in zoom animation, custom style color palettes, and a title card overlay
- Synchronizes video duration to the audio voiceover length

---

### 7. `run_pipeline.py` — Orchestrator

**Purpose:** Combines steps into a single CLI tool with safety guardrails.

**Behavior:**
- Picks a random style rotation (chaotic, meme, npc, story)
- Orchestrates download, segmenting, generation, synthesis, rendering, and publishing
- Implements a global pipeline alarm timeout of 40 minutes (guards against indefinite hangs)

---

### 8. `upload_instagram.py` — Automated Instagram & Facebook Reels Publisher

**Purpose:** Hosts local video on Cloudinary, publishes it as Instagram Reels, and optionally Facebook Page Reels.

**Workflow:**
1. **Cloudinary Upload**: Uploads `final_short.mp4` to Cloudinary via `cloudinary.uploader.upload_large()`.
2. **Instagram Reels**:
   - Creates a Reels container via the Meta Graph API `/media` endpoint pointing to the Cloudinary URL.
   - Polls container status via Graph API until `status_code` is `'FINISHED'`.
   - Publishes Reels container via `/media_publish` endpoint.
3. **Facebook Page Reels**:
   - Initializes a Reels session via Facebook Page `/video_reels` endpoint.
   - Posts the Cloudinary URL to the upload URL.
   - Publishes the Reel via `/video_reels` endpoint.
4. **Cloudinary Cleanup**: Automatically deletes the hosted video asset from Cloudinary in the `finally` block to conserve cloud storage space.

---

## GitHub Actions CI/CD

The pipeline has a scheduled workflow (`.github/workflows/daily_brainrot.yml`) that runs 4x daily.

**Key points:**
- Uses `--skip-download` because yt-dlp gets bot-blocked on GitHub runner IPs
- Relies on pre-committed clips in `data/clips/`
- Automated upload works via Cloudinary and Meta Page Access Token secrets

**Required GitHub Secrets:**
- `GROQ_API_KEY`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `IG_ACCESS_TOKEN`
- `IG_ACCOUNT_ID`
- `FB_PAGE_ID` (optional)
- `FB_PAGE_ACCESS_TOKEN` (optional)

---

## Known Issues & Workarounds

### yt-dlp Bot Block on CI
YouTube blocks yt-dlp requests from cloud IPs (GitHub runners). **Workaround:** The CI uses `--skip-download` and relies on pre-committed clips.

### Windows Path Colons in FFmpeg
The `subtitles` filter in FFmpeg parses colons as option separators. A path like `D:/folder/file.ass` breaks the filter graph. **Fix:** Use a relative path (`data/output/captions.ass`) instead of an absolute path.

### FFmpeg Pipe Buffer Deadlock
`subprocess.run(cmd, capture_output=True, text=True)` with ffmpeg causes a deadlock because ffmpeg fills the stderr pipe buffer, blocking both processes. **Fix:** Use `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`.

---

## Dependencies

```
groq>=0.12.0                 # LLM API client
python-dotenv>=1.0.0         # .env file loading
edge-tts>=6.1.0              # Free TTS
yt-dlp>=2024.0.0             # YouTube video download
cloudinary>=1.33.0           # Cloudinary SDK
requests>=2.31.0             # REST API communications
```

System dependency: **FFmpeg** (must be installed and in PATH)