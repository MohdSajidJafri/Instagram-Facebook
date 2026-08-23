"""
Render final 9:16 brainrot short with HIGH QUALITY.
- Lanczos upscale + unsharp for crisp 1080p
- Kinetic captions: emphasis words get 1.5x size, alternating placement
- Style-based color palettes
- Title card overlay at video start
- Word timings matched to voiceover speed
"""
from __future__ import annotations

import os
import random
import re
import subprocess
import sys
import tempfile
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

RENDER_TIMEOUT = 600
FFPROBE_TIMEOUT = 60

# Style-based color palettes (flashy & multicolored neon colors for brainrot feel)
STYLE_PALETTES = {
    "chaotic": ["&H000000FF", "&H0000A5FF", "&H0000FFFF", "&H00FF00FF", "&H00FFFF00", "&H0000FF00"], # Red, Orange, Yellow, Pink, Cyan, Green
    "meme":    ["&H0000FF00", "&H00FFFF00", "&H0000FFFF", "&H00FF00FF", "&H0000A5FF", "&H000000FF"], # Green, Cyan, Yellow, Pink, Orange, Red
    "story":   ["&H00FFFFFF", "&H0000FFFF", "&H00FFFF00", "&H00FF00FF", "&H0000FF00", "&H00FF5500"], # White, Yellow, Cyan, Pink, Green, Blue
    "npc":     ["&H00FF00FF", "&H00937FDC", "&H008A2BE2", "&H00FFFF00", "&H0000FF00", "&H00FFFFFF"], # Pink, Purple, Violet, Cyan, Green, White
}

ALTERNATE_Y = [1200, 1400, 1600, 1300, 1500, 1700]


def _get_dur(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True, timeout=FFPROBE_TIMEOUT)
    return float(r.stdout.strip())




def _build_word_timings(clean_words: list[str], audio_dur: float,
                        sentence_timings: list[dict] | None = None) -> list[tuple[float, float, str]]:
    """Build (start_sec, end_sec, word) tuples from sentence timestamps."""
    result = []
    n = len(clean_words)

    if sentence_timings and len(sentence_timings) > 0:
        word_idx = 0
        for sent in sentence_timings:
            s_text = sent.get("text", "")
            s_start = sent.get("offset_ms", 0) / 1000
            s_dur = sent.get("duration_ms", 1000) / 1000
            s_end = s_start + s_dur
            s_words = [w for w in s_text.split() if w.strip()]
            n_s_words = len(s_words)
            if n_s_words > 0 and word_idx < n:
                w_per = s_dur / n_s_words
                for j in range(n_s_words):
                    if word_idx >= n:
                        break
                    ws = s_start + j * w_per
                    we = min(ws + w_per, s_end)
                    result.append((ws, we, clean_words[word_idx]))
                    word_idx += 1
        remaining = n - word_idx
        if remaining > 0:
            last_end = result[-1][1] if result else audio_dur
            time_left = audio_dur - last_end
            w_per = time_left / max(remaining, 1)
            for j in range(remaining):
                ws = last_end + j * w_per
                we = min(ws + w_per, audio_dur)
                result.append((ws, we, clean_words[word_idx]))
                word_idx += 1
    else:
        w_per = audio_dur / max(n, 1)
        for i, w in enumerate(clean_words):
            ws = i * w_per
            we = min((i + 1) * w_per, audio_dur)
            result.append((ws, we, w))
    return result


def _build_ass_subtitles(
    timings: list[tuple[float, float, str]],
    style: str = "chaotic",
    emphasis_words: list[str] | None = None,
    video_title: str = "",
) -> str:
    """Build ASS subtitle content with kinetic styling and title card."""
    palette = STYLE_PALETTES.get(style, STYLE_PALETTES["chaotic"])
    emphasis_set = set(w.upper() for w in (emphasis_words or []))

    title = video_title.strip() or "GTA V BRAINROT"

    def _t(s):
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        return f"{h}:{m:02d}:{s % 60:05.2f}"

    ass = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Emphasis,Impact,130,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,5,5,0,0,0,1\n"
        "Style: Normal,Impact,90,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,5,5,0,0,0,1\n"
        "Style: Title,Impact,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,5,5,0,0,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    # Title card: show at video start for 2.5 seconds at top-center
    if timings:
        first_word_start = timings[0][0]
        title_duration = min(2.5, first_word_start + 0.3)
        title_color = palette[0]
        ass += f"Dialogue: 0,0:00:00.00,{_t(title_duration)},Title,,0,0,400,,{{\\c{title_color}\\an8}}{title}\n"

    # Word-by-word captions
    for i, (ts, te, w) in enumerate(timings):
        word_upper = w.strip(".,!?;:\"'").upper()
        is_emphasis = word_upper in emphasis_set
        style_name = "Emphasis" if is_emphasis else "Normal"
        color = palette[i % len(palette)]
        
        # Center-aligned exactly at (540, 1000) with a subtle scale pop-in animation.
        # Normal words pop from 125% to 100% size; Emphasis words pop from 130% to 100%.
        zoom_start = 130 if is_emphasis else 125
        ass += f"Dialogue: 0,{_t(ts)},{_t(te)},{style_name},,0,0,0,,{{\\c{color}\\an5\\pos(540,1000)\\fscx{zoom_start}\\fscy{zoom_start}\\t(0,80,\\fscx100\\fscy100)}}{w}\n"

    return ass


def render(
    clip_path: Path, audio_path: Path, narration: str,
    output_path: Path | None = None,
    sentence_timings: list[dict] | None = None,
    style: str = "chaotic",
    emphasis_words: list[str] | None = None,
    video_title: str = "",
) -> Path:
    if output_path is None:
        output_path = config.OUTPUT_DIR / "final_short.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clip_dur = _get_dur(clip_path)
    audio_dur = _get_dur(audio_path)
    print(f"🎬 {clip_dur:.0f}s clip + {audio_dur:.0f}s audio")

    clean = narration.replace("**", "").replace("__", "").replace("*", "")
    clean = re.sub(r'[^\w\s\'",.!?;:\-]', '', clean).strip()
    if not clean:
        clean = "GTA VI BRAINROT"
    words = clean.split()

    timings = _build_word_timings(words, audio_dur, sentence_timings)
    print(f"   {len(words)} words, {audio_dur:.0f}s audio, {len(sentence_timings or [])} sentences")

    # Build subtitles with title card
    title_display = video_title.strip() or "GTA V BRAINROT"
    ass = _build_ass_subtitles(timings, style, emphasis_words, title_display)

    ass_path = config.OUTPUT_DIR / "captions.ass"
    ass_path.write_text(ass, encoding="utf-8")

    # Format absolute path for FFmpeg subtitles filter on Windows
    ass_path_str = str(ass_path.resolve()).replace("\\", "/")
    ass_safe = ass_path_str.replace(":", "\\:")

    def _build_cmd(preset: str, crf: str, bv: str, ba: str) -> list[str]:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(clip_path),
            "-i", str(audio_path),
        ]
        
        # Build dynamic visual zoom expression synchronized with emphasis words
        zoom_intervals = []
        for start, end, word in timings:
            clean_word = word.strip(".,!?;:\"'-").upper()
            if clean_word in [e.upper() for e in emphasis_words]:
                zoom_intervals.append(f"between(t,{start:.3f},{end:.3f})")
        
        if zoom_intervals:
            sum_of_betweens = "+".join(zoom_intervals)
            zoom_expr = f"if({sum_of_betweens},0.88,1)"
        else:
            zoom_expr = "1"
            
        filter_complex = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale=1080:1920:flags=bicubic:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5[bg_blurred];"
            f"[fg]scale=1080:-2:flags=bicubic[fg_scaled];"
            f"[bg_blurred][fg_scaled]overlay=0:(H-h)/2,"
            f"crop=w='1080*{zoom_expr}':h='1920*{zoom_expr}':x='(iw-ow)/2':y='(ih-oh)/2',"
            f"scale=1080:1920:flags=bicubic,"
            f"fps={config.FPS},"
            f"unsharp=5:5:1.0:5:5:0.0,"
            f"subtitles='{ass_safe}'[v]"
        )
        
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", preset, "-crf", crf,
            "-b:v", bv, "-maxrate", bv, "-bufsize", str(int(bv.rstrip("M")) * 2) + "M",
            "-profile:v", "high", "-level", "4.2",
            "-r", str(config.FPS),
            "-c:a", "aac", "-b:a", ba, "-ar", "48000",
            "-shortest", "-movflags", "+faststart",
            str(output_path),
        ])
        return cmd

    presets = [
        ("medium", "16", "10M", "256k"),
        ("fast", "20", "6M", "192k"),
        ("slow", "16", "12M", "256k"),
    ]

    log_path = config.CACHE_DIR / "ffmpeg_render.log"
    with open(log_path, "w", encoding="utf-8") as log_file:
        for preset, crf, bv, ba in presets:
            cmd = _build_cmd(preset, crf, bv, ba)
            print(f"   Rendering ({preset}, {bv}, crf {crf})…")
            try:
                r = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT, timeout=RENDER_TIMEOUT)
            except subprocess.TimeoutExpired:
                print(f"   ⚠ {preset} timed out")
                continue
            if r.returncode == 0:
                break
            print(f"   ⚠ {preset} failed (code {r.returncode}). See log at {log_path}")
        else:
            print("❌ All render presets failed")
            sys.exit(1)

    if output_path.exists():
        mb = output_path.stat().st_size / 1_048_576
        d = _get_dur(output_path)
        print(f"   ✅ {output_path.name} ({mb:.0f}MB, {d:.0f}s)")
    return output_path


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--clip", required=True)
    a.add_argument("--audio", required=True)
    a.add_argument("--narration", default="GTA VI BRAINROT")
    a.add_argument("--style", default="chaotic")
    a.add_argument("--emphasis", default="")
    a.add_argument("--title", default="")
    args = a.parse_args()
    emphasis = [w.strip() for w in args.emphasis.split(",") if w.strip()] if args.emphasis else None
    render(Path(args.clip), Path(args.audio), args.narration, style=args.style,
           emphasis_words=emphasis, video_title=args.title)