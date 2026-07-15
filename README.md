# GTA VI Brainrot Reels Automation Pipeline

Fully automated pipeline to:
1. Download GTA VI gameplay clips from YouTube
2. Split into short segments via scene detection
3. Generate brainrot-style scripts via Groq LLM (free)
4. Synthesize voiceover via Edge TTS (free)
5. Overlay word-by-word captions (brainrot style)
6. Render 9:16 vertical MP4
7. Upload automatically to Instagram Reels and Facebook Page Reels via Cloudinary and Meta Graph API

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq LLM API key |
| `CLOUDINARY_CLOUD_NAME` | Yes | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Yes | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Yes | Cloudinary API secret |
| `IG_ACCESS_TOKEN` | Yes | Meta Graph API Access Token with `instagram_content_publish` |
| `IG_ACCOUNT_ID` | Yes | Instagram Business Account ID |
| `FB_PAGE_ID` | Optional | Facebook Page ID (for dual-publishing) |
| `FB_PAGE_ACCESS_TOKEN` | Optional | Facebook Page Access Token |

## Usage

**Full pipeline (one-shot):**
```bash
python run_pipeline.py
```

**Individual steps:**
```bash
python download_clips.py           # Download fresh GTA VI gameplay
python process_clips.py            # Split into short clips
python generate_script.py          # Generate brainrot scripts
python generate_voiceover.py       # TTS audio
python render_short.py             # Render final video with captions
python upload_instagram.py         # Upload to Instagram/Facebook Reels
```

## Daily Automation (GitHub Actions ready)

The pipeline is set up to run automatically 4x daily using the workflow in `.github/workflows/daily_brainrot.yml`. Configure the credentials listed above under Action Secrets in your GitHub repository settings.