"""
Generate brainrot scripts for GTA V clips using Groq LLM.
Target: 40-65 words, hook-first, definitive punchline, with emphasis keywords for kinetic captions.
Strict no-emoji policy in spoken script (Edge TTS safety).
"""
from __future__ import annotations

import os
import random
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import TypedDict

# Windows UTF-8 console safety
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from groq import Groq, RateLimitError

import config

# Forbidden/bannable words to ensure absolute content safety and brand protection
FORBIDDEN_WORDS = [
    "RAPE", "RAPED", "RAPING", "RAPIST", "NIGGER", "FAGGOT", "RETARD", "RETARDED",
    "SUICIDE", "KILL MYSELF", "KILL YOURSELF", "SLUT", "WHORE", "CUNT", "DICK",
    "PORN", "SEX", "PEDO", "PEDOPHILE", "TERRORIST", "BOMBING", "MASSACRE",
    "GOD", "JESUS", "ALLAH", "RELIGION", "RELIGIOUS", "CHURCH", "MOSQUE", "BIBLE", "QURAN",
    "PRAY", "PRAYER", "PRAYING", "HEAVEN", "HELL", "SATAN", "DEVIL", "CHRISTIAN", "MUSLIM",
    "JEW", "JEWISH", "BUDDHIST", "HINDU"
]

SCROLL_HOOKS = [
    "Nobody talks about this...",
    "I just realized something...",
    "This might be the dumbest thing I've ever noticed...",
    "Hear me out...",
    "I refuse to believe I'm the only one...",
    "Imagine if...",
    "This is either genius or completely stupid.",
    "I have a theory.",
    "How it feels to...",
]

FORMAT_CATEGORIES = [
    "FAKE LIFE ADVICE: Sound profound, but slowly become completely unhinged.",
    "CONSPIRACY BRAINROT: Start believable, then completely ruin it with absurd logic.",
    "NPC THOUGHTS: Reveal weird cashier, waiter, or stranger secrets.",
    "RANDOM FACTS (90% FAKE): Say completely fake things confidently to start comment wars.",
    "POV VIDEOS: High-relatability gamer or social situations.",
    "TIER LISTS: Rate completely random everyday things or habits.",
    "IMAGINE EXPLAINING THIS: Contrast modern absurdities with historical figures.",
    "THINGS EVERYONE DOES BUT NEVER ADMITS: Universal unhinged quirks and loops.",
    "FAKE MOTIVATIONAL SPEAKER: Speak like a clueless millionaire life coach.",
    "HOW IT FEELS: Hyper-specific relatable gamer or social emotions.",
    "RANKING PAIN LEVELS: Everyday mental or physical micro-traumas.",
    "INTERNET LORE: Make up ridiculous historical internet history.",
]

USER_SYSTEM_PROMPT = (
    "You write viral brainrot short-form video scripts for GTA V visual backdrops. "
    "The script topic must be completely random, weird, and unhinged brainrot humor (NOT gaming or NPC-focused). "
    "Strictly follow the assigned format and starting hook. "
    "Use plain text only in HOOK, BODY, and PUNCHLINE — strictly NO emojis, NO markdown, and NO asterisks in script narration. "
    "End with a definitive, punchy closing line with a full stop (do NOT loop). "
    "Keep all content safe-for-work, secular, advertiser-friendly, and free from sensitive or offensive terms.\n\n"
    "Output format EXACTLY:\n"
    "HOOK: <5-10 words starting with assigned hook>\n"
    "BODY: <3-5 short punchy lines, 25-45 words total>\n"
    "PUNCHLINE: <definitive funny closing punchline, 5-10 words>\n"
    "EMPHASIS: <comma-separated list of 2-3 ALL CAPS words>\n"
    "TITLE: <viral clickbait title under 55 chars with 1-2 shock emojis>"
)


class FallbackScript(TypedDict):
    narration: str
    title: str
    emphasis: list[str]


# Diverse pool of distinct, unhinged fallback scripts with definitive endings
FALLBACK_SCRIPTS: list[FallbackScript] = [
    {
        "narration": (
            "Nobody talks about this, but grocery carts with one broken wheel are cursed. "
            "You try to steer NORMAL, and suddenly you are drifting into the frozen aisle at MAXIMUM velocity. "
            "We are not shoppers, we are unpaid stunt drivers."
        ),
        "title": "Grocery Cart Curse 💀🛒",
        "emphasis": ["NORMAL", "MAXIMUM", "DRIVERS"],
    },
    {
        "narration": (
            "I just realized something terrifying about microwave buttons. "
            "Nobody has EVER used the defrost button on purpose. "
            "You either press plus thirty seconds ten times or you accept eating a FROZEN burrito in defeat."
        ),
        "title": "Microwave Secret Exposed 🤯📦",
        "emphasis": ["EVER", "DEFROST", "FROZEN"],
    },
    {
        "narration": (
            "This might be the dumbest thing I've ever noticed, but elevators are pure tension. "
            "Everyone stares at the floor numbers in intense SILENCE like it is the most CRITICAL data on earth. "
            "One sneeze and the entire room panics."
        ),
        "title": "Elevator Survival Guide 💀👀",
        "emphasis": ["SILENCE", "CRITICAL", "PANICS"],
    },
    {
        "narration": (
            "Hear me out on this. Your alarm clock does not wake you up. "
            "It simply alerts you that your daily TRIAL period of existing has officially begun. "
            "The snooze button is just a five minute micro transaction."
        ),
        "title": "Alarm Clock Matrix Glitch ⏰💀",
        "emphasis": ["TRIAL", "BEGUN", "TRANSACTION"],
    },
    {
        "narration": (
            "I refuse to believe I'm the only one who checks behind the shower curtain for INTRUDERS before using the bathroom. "
            "If someone is waiting in there with shampoo, at least I have the tactical ADVANTAGE. "
            "Paranoia is just advanced preparedness."
        ),
        "title": "Shower Curtain Protocol 🚿👀",
        "emphasis": ["INTRUDERS", "ADVANTAGE", "PREPAREDNESS"],
    },
    {
        "narration": (
            "Imagine if pigeons were actually charging rent for sitting on power lines. "
            "They sit up there judging your OUTFIT with zero remorse. "
            "The government gave them free flight and they chose pure CHAOS."
        ),
        "title": "Pigeon Conspiracy Uncovered 🐦💀",
        "emphasis": ["OUTFIT", "REMORSE", "CHAOS"],
    },
    {
        "narration": (
            "This is either genius or completely stupid, but socks disappear in the dryer because they ESCAPE into an alternate dimension. "
            "You start with twelve pairs and end up with three RANDOM singles and a mysterious guitar pick. "
            "The laundry tax is REAL."
        ),
        "title": "The Dryer Dimension Mystery 🧦🤯",
        "emphasis": ["ESCAPE", "RANDOM", "REAL"],
    },
    {
        "narration": (
            "I have a theory that whoever invented the phrase sleep like a baby never met one. "
            "Babies wake up screaming every TWO hours demanding food. "
            "I want to sleep like an UNEMPLOYED roommate on a Tuesday afternoon."
        ),
        "title": "Sleep Like A Baby Scam 😴💀",
        "emphasis": ["TWO", "SCREAMING", "UNEMPLOYED"],
    },
    {
        "narration": (
            "How it feels to make eye contact with a cashier while your CARD is getting declined. "
            "Your soul leaves your body and you suddenly FORGET your own zip code. "
            "Financial survival is a contact sport."
        ),
        "title": "Card Declined Trauma 💳💀",
        "emphasis": ["CARD", "FORGET", "SURVIVAL"],
    },
]


def _strip_emojis(text: str) -> str:
    """
    Comprehensive emoji, pictograph, and symbol removal using unicodedata
    and unicode regex to guarantee no emoji reaches Edge TTS.
    """
    if not text:
        return ""

    # Comprehensive regex covering standard emoji & pictograph unicode blocks
    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010FFFF"  # Supplementary Multilingual Planes (emojis, pictographs, symbols)
        "\U00002600-\U000027BF"  # Miscellaneous Symbols & Dingbats
        "\U00002300-\U000023FF"  # Miscellaneous Technical
        "\U00002B50-\U00002B55"  # Star / Circle symbols
        "\U0000200D"              # Zero-width joiner
        "\U0000FE0E-\U0000FE0F"  # Variation selectors
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)

    # Secondary sweep: check character category with unicodedata
    filtered_chars: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        # So: Symbol other, Sk: Symbol modifier, Cs: Surrogates, Cn: Unassigned
        if cat in ("So", "Sk", "Cs", "Cn"):
            continue
        filtered_chars.append(ch)

    cleaned = "".join(filtered_chars)
    return re.sub(r"\s+", " ", cleaned).strip()


def _strip_markdown(text: str) -> str:
    """Remove markdown bold, italic, code, and underline symbols from text."""
    if not text:
        return ""
    # Strip markdown symbols: **, *, `, __, ~~
    text = re.sub(r'[\*`_~]+', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _parse_structured_response(response: str) -> dict:
    """Parse the structured LLM response into components.
    Strips markdown formatting, bold/italics, and list bullets from headers and values.
    """
    result = {
        "hook": "",
        "body": "",
        "punchline": "",
        "emphasis": [],
        "full_narration": "",
        "title": "GTA V BRAINROT",
    }

    lines = response.splitlines()
    current_section = None
    sections: dict[str, str] = {}
    found_any_label = False

    # Regex to match labeled sections even with markdown markers, numbers, or bullets:
    # e.g., "**HOOK:**", "### HOOK:", "*HOOK*:", "1. HOOK:", "- HOOK:", "HOOK:"
    label_pattern = re.compile(
        r'^(?:[#*\-\d\.\s]*)(HOOK|BODY|PUNCHLINE|EMPHASIS|NARRATION|TITLE)\s*[:\-]\s*(.*)$',
        re.IGNORECASE
    )

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        match = label_pattern.match(line_str)
        if match:
            found_any_label = True
            label = match.group(1).upper()
            content = match.group(2).strip()

            if label == "HOOK":
                current_section = "hook"
                sections["hook"] = content
            elif label == "BODY":
                current_section = "body"
                sections["body"] = content
            elif label == "PUNCHLINE":
                current_section = "punchline"
                sections["punchline"] = content
            elif label == "EMPHASIS":
                current_section = "emphasis"
                raw_words = [w.strip().upper() for w in content.split(",") if w.strip()]
                # Strip markdown from emphasis words
                result["emphasis"] = [_strip_markdown(_strip_emojis(w)) for w in raw_words if w]
            elif label == "NARRATION":
                current_section = "narration"
                result["full_narration"] = content
            elif label == "TITLE":
                current_section = "title"
                result["title"] = _strip_markdown(content)[:60]
        elif current_section and current_section in sections:
            sections[current_section] = sections[current_section] + " " + line_str

    # Build structured result from sections
    if sections.get("hook") or sections.get("body") or sections.get("punchline"):
        result["hook"] = _strip_markdown(_strip_emojis(sections.get("hook", "")))
        result["body"] = _strip_markdown(_strip_emojis(sections.get("body", "")))
        result["punchline"] = _strip_markdown(_strip_emojis(sections.get("punchline", "")))
        parts = [p for p in [result["hook"], result["body"], result["punchline"]] if p]
        result["full_narration"] = " ".join(parts)
    elif result["full_narration"]:
        result["full_narration"] = _strip_markdown(_strip_emojis(result["full_narration"]))
    elif found_any_label:
        result["full_narration"] = _strip_markdown(_strip_emojis(response))
    else:
        # No labels found - treat entire response as free-form narration
        clean_resp = _strip_markdown(_strip_emojis(response))
        result["full_narration"] = clean_resp
        # Check if last line looks like a title
        last_line = lines[-1].strip() if lines else ""
        if last_line and len(last_line.split()) <= 8 and not last_line.endswith((".", "!", "?")):
            result["title"] = _strip_markdown(last_line)[:60]
            result["full_narration"] = _strip_markdown(_strip_emojis("\n".join(lines[:-1]))).strip()

    # Generate title from HOOK if no explicit TITLE was found
    if result["title"] == "GTA V BRAINROT" and result.get("hook"):
        hook_title = result["hook"].rstrip(".!?")
        hook_title = re.sub(r'[^\w\s\'-]', '', hook_title).strip()
        if hook_title:
            result["title"] = hook_title[:60]

    # If still default title, generate from first sentence of narration
    if result["title"] == "GTA V BRAINROT" and result["full_narration"]:
        first_sentence = result["full_narration"].split(".")[0].strip()
        if first_sentence and len(first_sentence) > 5:
            first_sentence = re.sub(r'[^\w\s\'-]', '', first_sentence).strip()
            if len(first_sentence) > 55:
                first_sentence = first_sentence[:55] + "..."
            result["title"] = first_sentence

    # Extract emphasis from narration if none extracted
    if not result["emphasis"] and result["full_narration"]:
        result["emphasis"] = _extract_emphasis_from_text(result["full_narration"])

    return result


def _extract_emphasis_from_text(text: str) -> list[str]:
    """Extract ALL CAPS words as emphasis targets."""
    words = text.split()
    caps_words = [w.strip(".,!?;:\"'-*`_") for w in words if w.isupper() and len(w) > 2]
    # Deduplicate while preserving order
    seen = set()
    return [w for w in caps_words if not (w in seen or seen.add(w))][:5]


def _get_random_fallback() -> tuple[str, str, list[str]]:
    """Pick a random fallback script from the diverse pool."""
    chosen = random.choice(FALLBACK_SCRIPTS)
    return chosen["narration"], chosen["title"], chosen["emphasis"]


def generate_brainrot_script(
    clip_description: str = "",
    style: str = "chaotic",
) -> tuple[str, str, list[str]]:
    """
    Generate a brainrot script using Groq LLM (openai/gpt-oss-20b).
    Returns: (full_narration, title, emphasis_words)
    """
    api_key = config.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not set!")
        sys.exit(1)

    client = Groq(api_key=api_key)

    # Randomly select a format category and a scroll hook
    selected_format = random.choice(FORMAT_CATEGORIES)
    selected_hook = random.choice(SCROLL_HOOKS)

    user_prompt = (
        f"Format Category: {selected_format}\n"
        f"Assigned Hook: Start your HOOK with '{selected_hook}'\n\n"
        f"Requirements:\n"
        f"- HOOK: 5-10 words, must start with '{selected_hook}'\n"
        f"- BODY: 3-5 short punchy lines (25-45 words total)\n"
        f"- PUNCHLINE: 5-10 words, definitive punchy conclusion ending with a full stop.\n"
        f"- Total word count across HOOK + BODY + PUNCHLINE must be 40-65 words.\n"
        f"- Capitalize 2-3 key words in ALL CAPS for emphasis.\n"
        f"- Strictly NO emojis in HOOK, BODY, or PUNCHLINE (emojis ONLY allowed in TITLE).\n"
        f"- NO markdown formatting (no asterisks, bold, or backticks).\n"
        f"- Do NOT loop back to the hook. End decisively with a definitive punchline.\n\n"
        f"Format EXACTLY as:\n"
        f"HOOK: <text>\n"
        f"BODY: <text>\n"
        f"PUNCHLINE: <text>\n"
        f"EMPHASIS: <word1, word2>\n"
        f"TITLE: <title with 1-2 emojis>"
    )

    print(f"🤖 Groq: generating script using [{selected_format.split(':')[0]}]…")

    best_result = {
        "full_narration": "",
        "title": "GTA V BRAINROT",
        "emphasis": [],
        "word_count": 0,
    }

    max_attempts = 2
    for attempt in range(max_attempts):
        if attempt > 0:
            time.sleep(2)

        try:
            completion = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": USER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.9,
                max_tokens=2048,
                timeout=35,
            )
        except RateLimitError as rle:
            print(f"   ⚠ Groq Rate Limit (429) hit on attempt {attempt+1}: {rle}")
            if attempt < max_attempts - 1:
                print("   ⏳ Sleeping 12s for TPM window backoff...")
                time.sleep(12)
                continue
            else:
                print("   ⚠ Rate limit persisted, using random fallback script")
                return _get_random_fallback()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower():
                print(f"   ⚠ Groq 429 Rate Limit on attempt {attempt+1}: {e}")
                if attempt < max_attempts - 1:
                    print("   ⏳ Sleeping 12s for TPM window backoff...")
                    time.sleep(12)
                    continue
            else:
                print(f"   ⚠ Groq API error (attempt {attempt+1}): {e}")

            if attempt == max_attempts - 1:
                print("   ⚠ Using random fallback narration")
                return _get_random_fallback()
            continue

        raw_content = completion.choices[0].message.content or ""
        response = raw_content.strip()
        if not response:
            print(f"   ⚠ Empty completion response on attempt {attempt+1}")
            continue

        # Parse structured response
        parsed = _parse_structured_response(response)

        # Enforce strict no-emoji and no-markdown on spoken narration
        narration = _strip_markdown(_strip_emojis(parsed["full_narration"]))
        title = _strip_markdown(parsed["title"])

        # Strict Brand Safety check: scan narration and title for forbidden/bannable terms
        combined_text = (narration + " " + title).upper()
        has_forbidden = False
        for forbidden in FORBIDDEN_WORDS:
            if re.search(r'\b' + re.escape(forbidden) + r'\b', combined_text):
                print(f"   ⚠ Safety filter triggered: found forbidden word '{forbidden}' - retrying...")
                has_forbidden = True
                break

        if has_forbidden:
            continue

        # Get emphasis words (cleaned and stripped)
        emphasis = [_strip_markdown(_strip_emojis(w)) for w in parsed["emphasis"] if w]
        if not emphasis:
            emphasis = _extract_emphasis_from_text(narration)

        wc = len(narration.split())
        if wc > best_result["word_count"] and wc >= 25:
            best_result["full_narration"] = narration
            best_result["title"] = title or "GTA V BRAINROT 💀"
            best_result["emphasis"] = emphasis
            best_result["word_count"] = wc

        if 35 <= wc <= 75:
            break
        user_prompt += "\n\nMake it concise and punchy! MUST be 40-65 words total."

    # If we got nothing useful after all attempts, use fallback
    if not best_result["full_narration"]:
        print("   ⚠ No valid script generated, using random fallback")
        return _get_random_fallback()

    print(f"   📝 {best_result['word_count']} words, {len(best_result['emphasis'])} emphasis words")
    return best_result["full_narration"], best_result["title"], best_result["emphasis"]


# Backward compatibility for old code that expects 2 return values
def generate_brainrot_script_legacy(
    clip_description: str = "",
    style: str = "chaotic",
) -> tuple[str, str]:
    """Legacy wrapper that returns (narration, title) without emphasis."""
    narration, title, _ = generate_brainrot_script(clip_description, style)
    return narration, title


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="chaotic")
    args = ap.parse_args()
    n, t, e = generate_brainrot_script(style=args.style)
    print(f"\n✅ {len(n.split())} words: {n}")
    print(f"📌 Title: {t}")
    print(f"🔍 Emphasis: {e}")