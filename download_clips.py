"""
Download GTA VI gameplay clips from YouTube using yt-dlp.
Tracks already-downloaded videos to avoid duplicates.
Includes 403 bypass args and CLI options for query and count.
"""
from __future__ import annotations

import argparse
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


def download_fresh_clips(
    query: str | None = None,
    max_downloads: int | None = None,
) -> list[Path]:
    """
    Search YouTube for GTA V gameplay, download new videos.
    Uses android/web player client to bypass YouTube 403 throttling.
    Returns list of downloaded file paths (empty if none found).
    """
    search_query = query or config.YTDL_SEARCH_QUERY
    count = max_downloads if max_downloads is not None else config.YTDL_MAX_DOWNLOADS
    output_tpl = str(config.RAW_DIR / "%(id)s.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--format", config.YTDL_FORMAT,
        "--output", output_tpl,
        "--max-downloads", str(count),
        "--download-archive", str(config.CACHE_DIR / "archive.txt"),
        "--no-playlist",
        "--quiet",
        "--print", "after_move:filepath",
        "--extractor-args", "youtube:player_client=android,web",
        "--extractor-retries", "2",
        "--retries", "3",
        f"ytsearch{count}:{search_query}",
    ]

    print(f"🔍 Searching: {search_query}")
    print(f"   Max downloads: {count}")
    print(f"   Format: {config.YTDL_FORMAT}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        print(f"⚠ Download timed out after 180s — YouTube is likely blocking this environment")
        print("   → This is common on GitHub runners / cloud IPs")
        print("   → Run 'python download_clips.py' locally on your PC instead")
        return []

    if result.returncode != 0:
        print(f"⚠ Download failed: YouTube may be blocking this environment")
        if "Sign in" in result.stderr or "403" in result.stderr:
            print("   → YouTube anti-bot triggered (common on cloud runners)")
            print("   → Committed fallback clips in data/clips/ will be used")
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
    parser = argparse.ArgumentParser(description="Download gameplay clips via yt-dlp")
    parser.add_argument("--query", "-q", default=None, help="YouTube search query")
    parser.add_argument("--count", "-c", type=int, default=None, help="Max number of clips to download")
    args = parser.parse_args()

    files = download_fresh_clips(query=args.query, max_downloads=args.count)
    if not files:
        print("No new clips downloaded. Existing raw files:")
        for f in list_existing_raw():
            print(f"  {f.name}")
    sys.exit(0)