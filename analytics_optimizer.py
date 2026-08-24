"""
Meta Graph Analytics & Retention Self-Optimization Engine.
Connects directly to the Meta Graph API (v19.0/v20.0) to fetch Instagram Reels
and Facebook Reels insights, calculates viewer retention and style performance,
and outputs dynamic parameters to optimize short-form video generation.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, TypedDict

# Windows UTF-8 console safety
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import requests
import config

INTELLIGENCE_FILE = config.CACHE_DIR / "analytics_intelligence.json"
GRAPH_API_VERSION = getattr(config, "IG_API_VERSION", "v20.0")

DEFAULT_INTELLIGENCE: dict[str, Any] = {
    "last_synced_at": 0,
    "status": "baseline_default",
    "retention_profile": {
        "avg_watch_time_sec": 14.5,
        "avg_completion_rate": 0.65,
        "retention_status": "optimal_retention_extended",
    },
    "script_targets": {
        "target_word_count_min": 40,
        "target_word_count_max": 58,
        "target_video_duration_min": 18,
        "target_video_duration_max": 28,
    },
    "style_weights": {
        "chaotic": 0.35,
        "meme": 0.35,
        "story": 0.15,
        "npc": 0.15,
    },
    "metrics_summary": {
        "instagram_reels_analyzed": 0,
        "facebook_reels_analyzed": 0,
        "total_plays": 0,
        "total_shares": 0,
        "total_interactions": 0,
    },
}


def _get_meta_credentials() -> tuple[str, str, str, str]:
    """Retrieve Meta Graph API credentials from environment/config."""
    # Support both new and existing credential naming conventions
    access_token = (
        os.environ.get("META_ACCESS_TOKEN")
        or config.IG_ACCESS_TOKEN
        or config.FB_PAGE_ACCESS_TOKEN
        or os.environ.get("PAGE_ACCESS_TOKEN")
        or ""
    )
    ig_user_id = os.environ.get("IG_USER_ID") or config.IG_ACCOUNT_ID or ""
    fb_page_id = os.environ.get("FB_PAGE_ID") or config.FB_PAGE_ID or ""
    api_version = os.environ.get("IG_API_VERSION") or config.IG_API_VERSION or "v20.0"
    return access_token, ig_user_id, fb_page_id, api_version


def fetch_instagram_insights(
    access_token: str,
    ig_user_id: str,
    api_version: str = "v20.0",
) -> list[dict[str, Any]]:
    """
    Fetch recent Instagram Reels and their detailed performance insights.
    Queries /media then /{media_id}/insights for plays, reach, interactions, shares, watch time.
    """
    if not access_token or not ig_user_id:
        print("   ℹ Meta Graph: IG credentials not set, skipping IG insights")
        return []

    url = f"https://graph.facebook.com/{api_version}/{ig_user_id}/media"
    params = {
        "fields": "id,caption,timestamp,media_type,like_count,comments_count",
        "limit": "25",
        "access_token": access_token,
    }

    try:
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            print(f"   ⚠ Meta Graph IG media error ({resp.status_code}): {resp.text[:120]}")
            return []
        data = resp.json().get("data", [])
    except Exception as e:
        print(f"   ⚠ Failed to query IG media endpoint: {e}")
        return []

    reels_insights: list[dict[str, Any]] = []
    print(f"   📊 Analyzing {len(data)} recent Instagram post(s)…")

    for item in data:
        media_id = item.get("id")
        caption = item.get("caption", "") or ""
        media_type = item.get("media_type", "")

        # Target video / reels media types
        if media_type not in ("VIDEO", "REELS"):
            continue

        insight_url = f"https://graph.facebook.com/{api_version}/{media_id}/insights"
        insight_params = {
            "metric": "plays,reach,total_interactions,saved,shares,ig_reels_avg_watch_time",
            "access_token": access_token,
        }

        insights_map: dict[str, float] = {
            "plays": 0.0,
            "reach": 0.0,
            "total_interactions": 0.0,
            "saved": 0.0,
            "shares": 0.0,
            "ig_reels_avg_watch_time": 0.0,
        }

        try:
            i_resp = requests.get(insight_url, params=insight_params, timeout=15)
            if i_resp.status_code == 200:
                metrics_list = i_resp.json().get("data", [])
                for m in metrics_list:
                    name = m.get("name")
                    values = m.get("values", [])
                    if values and isinstance(values[0], dict):
                        insights_map[name] = float(values[0].get("value", 0))
                    elif "value" in m:
                        insights_map[name] = float(m.get("value", 0))
        except Exception:
            pass  # Fallback to basic metrics if insights query has restrictions

        reels_insights.append({
            "media_id": media_id,
            "caption": caption,
            "like_count": item.get("like_count", 0),
            "comments_count": item.get("comments_count", 0),
            **insights_map,
        })

    return reels_insights


def fetch_facebook_insights(
    access_token: str,
    fb_page_id: str,
    api_version: str = "v20.0",
) -> list[dict[str, Any]]:
    """
    Fetch recent Facebook Page videos/reels and their video insights.
    """
    if not access_token or not fb_page_id:
        print("   ℹ Meta Graph: FB Page credentials not set, skipping FB insights")
        return []

    url = f"https://graph.facebook.com/{api_version}/{fb_page_id}/videos"
    params = {
        "fields": "id,title,description,created_time,views",
        "limit": "25",
        "access_token": access_token,
    }

    try:
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            print(f"   ⚠ Meta Graph FB videos error ({resp.status_code}): {resp.text[:120]}")
            return []
        data = resp.json().get("data", [])
    except Exception as e:
        print(f"   ⚠ Failed to query FB videos endpoint: {e}")
        return []

    fb_insights: list[dict[str, Any]] = []
    print(f"   📊 Analyzing {len(data)} recent Facebook video(s)…")

    for item in data:
        video_id = item.get("id")
        desc = item.get("description", "") or item.get("title", "") or ""
        views = float(item.get("views", 0) or 0)

        insight_url = f"https://graph.facebook.com/{api_version}/{video_id}/video_insights"
        insight_params = {
            "metric": "total_video_views,total_video_avg_time_watched",
            "access_token": access_token,
        }

        avg_time = 0.0
        try:
            i_resp = requests.get(insight_url, params=insight_params, timeout=15)
            if i_resp.status_code == 200:
                metrics_list = i_resp.json().get("data", [])
                for m in metrics_list:
                    name = m.get("name")
                    values = m.get("values", [])
                    if values and isinstance(values[0], dict):
                        val = float(values[0].get("value", 0))
                        if "avg_time_watched" in name:
                            avg_time = val / 1000.0 if val > 1000 else val  # Convert ms to sec if needed
                        elif "views" in name and val > views:
                            views = val
        except Exception:
            pass

        fb_insights.append({
            "video_id": video_id,
            "description": desc,
            "views": views,
            "avg_time_watched": avg_time,
        })

    return fb_insights


def _classify_style_from_text(text: str) -> str:
    """Detect brainrot style from caption text or hashtags."""
    t = text.lower()
    if "meme" in t:
        return "meme"
    if "story" in t or "lore" in t:
        return "story"
    if "npc" in t:
        return "npc"
    if "chaotic" in t or "chaos" in t:
        return "chaotic"
    return "chaotic"


def calculate_optimization_intelligence(
    ig_reels: list[dict[str, Any]],
    fb_videos: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Process raw Meta analytics into actionable tuning parameters:
    1. Retention tuning (target word counts & durations)
    2. Style performance weighting for probabilistic sampling
    """
    intelligence = dict(DEFAULT_INTELLIGENCE)
    intelligence["last_synced_at"] = int(time.time())

    total_ig = len(ig_reels)
    total_fb = len(fb_videos)

    if total_ig == 0 and total_fb == 0:
        intelligence["status"] = "baseline_default"
        return intelligence

    intelligence["status"] = "optimized_live_data"

    # ── 1. Calculate Retention Metrics ──
    watch_times: list[float] = []
    total_plays = 0
    total_shares = 0
    total_interactions = 0

    style_scores: dict[str, float] = {"chaotic": 1.0, "meme": 1.0, "story": 1.0, "npc": 1.0}

    for reel in ig_reels:
        plays = reel.get("plays", 0) or reel.get("reach", 0) or 0
        shares = reel.get("shares", 0) or 0
        interactions = reel.get("total_interactions", 0) or (reel.get("like_count", 0) + reel.get("comments_count", 0))
        watch_time = reel.get("ig_reels_avg_watch_time", 0.0)

        total_plays += int(plays)
        total_shares += int(shares)
        total_interactions += int(interactions)

        if watch_time > 0:
            watch_times.append(watch_time)

        # Style score calculation: plays + 3x shares + 2x interactions
        style = _classify_style_from_text(reel.get("caption", ""))
        style_scores[style] += plays + (shares * 3.0) + (interactions * 2.0)

    for vid in fb_videos:
        views = vid.get("views", 0) or 0
        avg_time = vid.get("avg_time_watched", 0.0)
        total_plays += int(views)

        if avg_time > 0:
            watch_times.append(avg_time)

        style = _classify_style_from_text(vid.get("description", ""))
        style_scores[style] += views

    # Retention Calculation
    avg_watch_time = sum(watch_times) / len(watch_times) if watch_times else 14.0
    # Standard short baseline length is ~22 seconds
    estimated_completion_rate = min(1.0, avg_watch_time / 22.0)

    # Low retention threshold: < 60% completion rate (< ~13s avg watch time)
    if estimated_completion_rate < 0.60:
        # Turbo-short mode: dial script down to 35-48 words for maximum completion & loops
        script_targets = {
            "target_word_count_min": 35,
            "target_word_count_max": 48,
            "target_video_duration_min": 14,
            "target_video_duration_max": 20,
        }
        retention_status = "low_retention_turbo_short"
    else:
        # Standard/extended retention mode
        script_targets = {
            "target_word_count_min": 45,
            "target_word_count_max": 60,
            "target_video_duration_min": 20,
            "target_video_duration_max": 30,
        }
        retention_status = "optimal_retention_extended"

    # ── 2. Calculate Normalized Style Weights ──
    total_score = sum(style_scores.values())
    if total_score > 0:
        normalized_weights = {
            k: round(v / total_score, 4) for k, v in style_scores.items()
        }
    else:
        normalized_weights = {"chaotic": 0.35, "meme": 0.35, "story": 0.15, "npc": 0.15}

    intelligence["retention_profile"] = {
        "avg_watch_time_sec": round(avg_watch_time, 2),
        "avg_completion_rate": round(estimated_completion_rate, 2),
        "retention_status": retention_status,
    }
    intelligence["script_targets"] = script_targets
    intelligence["style_weights"] = normalized_weights
    intelligence["metrics_summary"] = {
        "instagram_reels_analyzed": total_ig,
        "facebook_reels_analyzed": total_fb,
        "total_plays": total_plays,
        "total_shares": total_shares,
        "total_interactions": total_interactions,
    }

    return intelligence


def sync_and_optimize(force_refresh: bool = False) -> dict[str, Any]:
    """
    Sync live Meta Graph Insights, calculate retention & style weights,
    and save intelligence to data/cache/analytics_intelligence.json.
    """
    # Check cache freshness (refresh if older than 3 hours or forced)
    if not force_refresh and INTELLIGENCE_FILE.exists():
        try:
            with open(INTELLIGENCE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            last_synced = cached.get("last_synced_at", 0)
            if time.time() - last_synced < 3 * 3600:
                return cached
        except Exception:
            pass

    print("📡 Meta Graph Analytics: Syncing latest Instagram & Facebook Insights…")
    token, ig_user, fb_page, api_ver = _get_meta_credentials()

    ig_data: list[dict[str, Any]] = []
    fb_data: list[dict[str, Any]] = []

    if token:
        if ig_user:
            ig_data = fetch_instagram_insights(token, ig_user, api_ver)
        if fb_page:
            fb_data = fetch_facebook_insights(token, fb_page, api_ver)

    intelligence = calculate_optimization_intelligence(ig_data, fb_data)

    # Persist to cache
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(INTELLIGENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(intelligence, f, indent=2)

    print(f"   🧠 Intelligence updated: {intelligence['status']}")
    print(f"   🎯 Target word count: {intelligence['script_targets']['target_word_count_min']}–{intelligence['script_targets']['target_word_count_max']} words")
    print(f"   🎲 Style weights: {intelligence['style_weights']}")

    return intelligence


def get_cached_intelligence() -> dict[str, Any]:
    """Read cached analytics intelligence, returning defaults if not found."""
    if INTELLIGENCE_FILE.exists():
        try:
            with open(INTELLIGENCE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_INTELLIGENCE


if __name__ == "__main__":
    intel = sync_and_optimize(force_refresh=True)
    print("\n" + "=" * 60)
    print("📈 META GRAPH ANALYTICS INTELLIGENCE REPORT")
    print("=" * 60)
    print(json.dumps(intel, indent=2))
