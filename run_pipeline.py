#!/usr/bin/env python3
"""
GTA / GTA V Brainrot Shorts — Full Automation Pipeline.
Self-optimizing closed loop with Meta Graph Analytics.
Supports Instagram Reels & Facebook Page Reels automated uploads.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import signal
import subprocess
import sys
import threading
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
from analytics_optimizer import sync_and_optimize, get_cached_intelligence
from download_clips import download_fresh_clips, list_existing_raw
from process_clips import process_all_raw, get_random_clip
from generate_script import generate_brainrot_script, _strip_emojis
from generate_voiceover import synthesize_brainrot_voiceover
from render_short import render

STYLES = ["chaotic", "meme", "story", "npc"]

# Global timeout for the entire pipeline (40 min — CI has 45 min limit)
PIPELINE_TIMEOUT = 40 * 60  # 40 minutes in seconds

# Dynamic hashtag pools (ensuring <= 7 total tags to avoid Meta anti-spam throttling)
CORE_TAGS = ["#GTA6", "#GTAVI", "#gaming", "#brainrot"]
NICHE_TAG_POOL = [
    "#funny", "#relatable", "#comedy", "#unhinged", "#memes",
    "#satisfying", "#viralreels", "#gamermoments", "#gtafunny", "#gamingcommunity"
]
IG_PLATFORM_TAGS = ["#reels", "#fyp"]
FB_PLATFORM_TAGS = ["#FacebookReels", "#FBGaming"]

# High-CTR Call-to-Actions
CTA_POOL = [
    "Wait for the ending... 🤯 Follow for daily chaotic clips!",
    "Did not expect that to happen 💀 Drop a follow for more!",
    "Watch till the very end 💀 Follow for daily unhinged clips!",
    "Send this to a friend who does this 😂 Follow for daily brainrot!",
    "Save this before it gets taken down 🤯 Follow for more!",
    "POV: Peak GTA physics 💀 Follow @gyattwire for daily reels!",
]


def _pick_style(force: str | None) -> str:
    """
    Pick a style probabilistically based on learned weights from Meta Graph Analytics.
    Falls back to uniform random selection if forced or unconfigured.
    """
    if force and force != "random":
        return force

    intel = get_cached_intelligence()
    weights_dict = intel.get("style_weights", {})

    styles = []
    weights = []
    for s in STYLES:
        w = float(weights_dict.get(s, 0.25))
        styles.append(s)
        weights.append(w)

    # Normalize weights if sum > 0
    total_w = sum(weights)
    if total_w > 0:
        weights = [w / total_w for w in weights]
        chosen = random.choices(styles, weights=weights, k=1)[0]
        print(f"   🎲 Style chosen via analytics weights: {chosen.upper()} ({weights_dict.get(chosen, 0.25)*100:.1f}% weight)")
        return chosen

    return random.choice(STYLES)


def _generate_hashtags(platform: str = "instagram") -> str:
    """
    Mix core tags with 2-3 randomly sampled niche tags, keeping total <= 7 tags.
    """
    platform_tags = IG_PLATFORM_TAGS if platform == "instagram" else FB_PLATFORM_TAGS
    sampled_niche = random.sample(NICHE_TAG_POOL, k=random.randint(2, 3))
    all_tags = CORE_TAGS + platform_tags + sampled_niche

    # Deduplicate while preserving order
    seen = set()
    unique_tags = [t for t in all_tags if not (t in seen or seen.add(t))]
    return " ".join(unique_tags[:7])


def _build_description(style: str, title: str, platform: str = "instagram") -> str:
    """Build high-CTR catchy description with dynamic rotating hashtags and CTAs."""
    hooks = {
        "chaotic": [
            "Absolute CHAOS in GTA 6 🤯 Watch till the end!",
            "This is why GTA VI is the BEST game ever made 💀",
            "GTA 6 physics are BROKEN and I love it 😂",
        ],
        "meme": [
            "GTA 6 memes never get old 😂 Watch this!",
            "Only in GTA VI would this happen 💀",
            "This is PEAK GTA 6 content right here 🏆",
        ],
        "story": [
            "Every NPC in GTA 6 has a story 📖 This one is CRAZY",
            "The lore behind GTA VI NPCs is DEEP 😱",
            "This NPC has SEEN things in GTA 6 👀",
        ],
        "npc": [
            "POV: You're an NPC in GTA VI watching the player 💀",
            "The NPC experience in GTA 6 is UNDERRATED 😂",
            "NPCs in GTA VI have enough trauma for a lifetime 💀",
        ],
    }
    hook = random.choice(hooks.get(style, hooks["chaotic"]))
    cta = random.choice(CTA_POOL)
    hashtags = _generate_hashtags(platform)
    return f"{title}\n\n{hook}\n{cta}\n.\n.\n{hashtags}"


def main() -> None:
    # Set an overall pipeline alarm timeout
    timer = threading.Timer(PIPELINE_TIMEOUT, lambda: (
        print(f"\n❌ PIPELINE TIMEOUT after {PIPELINE_TIMEOUT//60} minutes — aborting"),
        os._exit(1)
    ))
    timer.daemon = True
    timer.start()

    try:
        ap = argparse.ArgumentParser(
            description="GTA V Brainrot Shorts — Full Automation Pipeline"
        )
        ap.add_argument("--no-upload", action="store_true", help="Skip Instagram/Facebook Reels upload")
        ap.add_argument("--skip-download", action="store_true", help="Skip downloading new clips")
        ap.add_argument("--style", default="random",
                        choices=["random", "chaotic", "meme", "story", "npc"],
                        help="Brainrot style (default: probabilistic analytics rotation)")
        args = ap.parse_args()

        print("=" * 60)
        print("🎮 GTA V BRAINROT SHORTS PIPELINE  |  SELF-OPTIMIZING FEEDBACK LOOP")
        print("=" * 60)

        # ── Step 0: Meta Graph Analytics Intelligence Sync ──
        print("\n📈 Step 0/7: Syncing Meta Graph Analytics & Retention Intelligence…")
        try:
            intel = sync_and_optimize()
            retention_status = intel.get("retention_profile", {}).get("retention_status", "optimal")
            print(f"   Status: {retention_status} | Target: {intel['script_targets']['target_word_count_min']}–{intel['script_targets']['target_word_count_max']} words")
        except Exception as e:
            print(f"   ⚠ Analytics sync fallback: {e}")

        style = _pick_style(args.style)
        print(f"   Active Style: {style.upper()}")

        # ── Step 1: Download ──
        if not args.skip_download:
            print(f"\n📥 Step 1/7: Downloading fresh GTA V gameplay clips…")
            new_clips = download_fresh_clips()
            if new_clips:
                print(f"   Downloaded {len(new_clips)} new video(s)")
        else:
            print(f"\n📥 Step 1/7: Skipping download")

        # ── Step 2: Process or use existing clips ──
        clips = []
        if args.skip_download:
            print(f"\n✂️  Step 2/7: Using pre-committed clips from data/clips/…")
            clips = sorted(config.CLIPS_DIR.glob("*.mp4"))
            if clips:
                print(f"   Found {len(clips)} committed clip(s)")
        if not clips:
            print(f"\n✂️  Step 2/7: Processing raw videos into short clips…")
            clips = process_all_raw()
        if not clips:
            print("⚠ No clips available from downloads.")
            print("   Generating a fallback test clip (solid color + text)…")
            fallback = config.CLIPS_DIR / "fallback.mp4"
            try:
                subprocess.run([
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", "color=c=#1a1a2e:s=1920x1080:d=40:r=30",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-vf", "drawtext=text='GTA V Gameplay':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-shortest",
                    str(fallback),
                ], capture_output=True, text=True, timeout=60)
            except subprocess.TimeoutExpired:
                print("   ⚠ Fallback clip generation timed out")
                print("❌ Cannot proceed without any clip")
                sys.exit(1)
            if fallback.exists():
                clips = [fallback]
                print(f"   ✅ Created fallback clip: {fallback.name}")
            else:
                print("❌ Could not create fallback clip either")
                sys.exit(1)

        # ── Step 3: Pick clip via anti-duplication rotation ──
        print(f"\n🎲 Step 3/7: Selecting a gameplay clip via anti-duplication rotation…")
        clip = get_random_clip()
        if not clip:
            print("❌ No clips in data/clips/")
            sys.exit(1)
        print(f"   Selected: {clip.name}")

        # ── Step 4: Generate script with adaptive word count ──
        print(f"\n🧠 Step 4/7: Generating retention-tuned {style} brainrot script…")
        narration, title, emphasis_words = generate_brainrot_script(style=style)
        print(f"   Emphasis words: {emphasis_words}")

        # Clean the narration BEFORE both TTS and rendering to keep word counts in sync
        import re
        clean_narration = narration.replace("**", "").replace("__", "").replace("*", "").replace("`", "")
        clean_narration = _strip_emojis(clean_narration)
        clean_narration = re.sub(r'[^\w\s\'",.!?;:\-]', '', clean_narration).strip()
        if not clean_narration:
            clean_narration = "GTA V BRAINROT"

        # Style-based TTS voice selection
        style_voices = {
            "chaotic": "en-US-AndrewMultilingualNeural",
            "meme": "en-US-AndrewMultilingualNeural",
            "story": "en-US-BrianMultilingualNeural",
            "npc": "en-US-BrianMultilingualNeural",
        }
        tts_voice = style_voices.get(style, config.TTS_VOICE)

        # ── Step 5: TTS ──
        print(f"\n🔊 Step 5/7: Synthesizing voiceover ({tts_voice})…")
        audio_path = config.OUTPUT_DIR / "voiceover.mp3"
        audio_dur, sentence_timings = synthesize_brainrot_voiceover(
            clean_narration, output_path=audio_path, voice=tts_voice,
        )

        # ── Step 6: Render ──
        print(f"\n🎬 Step 6/7: Rendering final 9:16 short with kinetic captions…")
        video_path = config.OUTPUT_DIR / "final_short.mp4"
        render(clip, audio_path, clean_narration, output_path=video_path,
               sentence_timings=sentence_timings, style=style,
               emphasis_words=emphasis_words, video_title=title)

        # ── Step 7: Upload ──
        if not args.no_upload:
            print(f"\n📤 Step 7/7: Upload phase…")

            ig_desc = _build_description(style, title, "instagram")
            fb_desc = _build_description(style, title, "facebook")

            from upload_instagram import upload_reel
            upload_reel(video_path, caption=ig_desc, fb_caption=fb_desc)
        else:
            print(f"\n⏭ Skipping upload (--no-upload)")

        print(f"\n{'=' * 60}")
        print(f"✅ PIPELINE COMPLETE!  ({style.upper()} style)")
        print(f"   Video: {video_path}")
        print(f"{'=' * 60}")

    finally:
        timer.cancel()


if __name__ == "__main__":
    main()