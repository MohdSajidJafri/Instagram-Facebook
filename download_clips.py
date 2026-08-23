"""
Download GTA VI gameplay clips from YouTube using yt-dlp.
Tracks already-downloaded videos to avoid duplicates.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Windows UTF-8 console safety
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import config





def download_fresh_clips() -> list[Path]:
    """
    Search YouTube for GTA V gameplay, download new videos.
    Works best on local machine (GitHub runners may get bot-blocked).
    Falls back gracefully if download fails.
    Returns list of downloaded file paths (empty if none found).
    """
    output_tpl = str(config.RAW_DIR / "%(id)s.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--format", config.YTDL_FORMAT,
        "--output", output_tpl,
        "--max-downloads", str(config.YTDL_MAX_DOWNLOADS),
        "--download-archive", str(config.CACHE_DIR / "archive.txt"),
        "--no-playlist",
        "--quiet",
        "--print", "after_move:filepath",
        "--extractor-retries", "1",
        "--retries", "2",
        f"ytsearch{config.YTDL_MAX_DOWNLOADS}:{config.YTDL_SEARCH_QUERY}",
    ]

    print(f"🔍 Searching: {config.YTDL_SEARCH_QUERY}")
    print(f"   Max downloads: {config.YTDL_MAX_DOWNLOADS}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"⚠ Download timed out after 120s — YouTube is likely blocking this environment")
        print("   → This is common on GitHub runners / cloud IPs")
        print("   → Run 'python download_clips.py' locally on your PC instead")
        return []

    if result.returncode != 0:
        print(f"⚠ Download failed: YouTube may be blocking this environment")
        if "Sign in" in result.stderr:
            print("   → YouTube requires sign-in (common on GitHub runners)")
            print("   → Run 'python download_clips.py' locally on your PC instead")
            print("   → The committed clips in this repo will be used")
        else:
            print(f"   Error: {result.stderr[:200]}")
        return []

    downloaded = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line:
            p = Path(line)
            if p.exists():
                downloaded.append(p)
                print(f"   ✅ Downloaded: {p.name}")

    print(f"   Total: {len(downloaded)} new video(s)")
    return downloaded


def list_existing_raw() -> list[Path]:
    """List all previously downloaded raw videos."""
    return sorted(config.RAW_DIR.glob("*.*"))


if __name__ == "__main__":
    files = download_fresh_clips()
    if not files:
        print("No new clips. Existing raw files:")
        for f in list_existing_raw():
            print(f"  {f.name}")
    sys.exit(0)