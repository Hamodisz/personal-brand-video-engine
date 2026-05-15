#!/usr/bin/env python3
"""
Script Agent — generates a TikTok script AND pre-builds the engine_config.json
so when you film and drop the video in, VisualPersonalityEngine already knows exactly
what to do: which words to emphasize, when to zoom, when to show personality labels,
when the CTA starts, everything.

Usage:
    python3 bin/script_agent.py --topic "why you quit every sport"
    python3 bin/script_agent.py --topic "sport personality types" --personality competitive_dark
    python3 bin/script_agent.py --topic "why team sports aren't for everyone" --lang en
"""

import json, os, sys, argparse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent

VISUAL_PERSONALITIES = {
    "competitive_dark": {
        "accent_color": "#6c63ff", "label_color": "#a855f7", "bg": "#06060f",
        "zoom_intensity": 1.07, "shake_intensity": 8, "scan_opacity_max": 0.22,
        "vibe": "dark, intense, cinematic. Feels like the viewer is being analyzed.",
    },
    "calm_analytical": {
        "accent_color": "#0ea5e9", "label_color": "#38bdf8", "bg": "#020d1a",
        "zoom_intensity": 1.03, "shake_intensity": 3, "scan_opacity_max": 0.12,
        "vibe": "calm, clean, analytical. Blue tones. Feels like a data-driven insight.",
    },
    "energetic_social": {
        "accent_color": "#f97316", "label_color": "#fb923c", "bg": "#0a0500",
        "zoom_intensity": 1.09, "shake_intensity": 10, "scan_opacity_max": 0.15,
        "vibe": "high energy, warm tones. Fast cuts. Feels like team sports culture.",
    },
}

def ask_claude(prompt: str, max_tokens: int = 3000) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        for f in [ROOT / ".env.local", ROOT / ".env"]:
            if f.exists():
                for line in f.read_text().splitlines():
                    if line.startswith("ANTHROPIC_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"\'')
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["content"][0]["text"]


REMOTION_STYLES = """
Available Remotion styles for SmartEdit:
- talking_head: full screen source video, dark background
- broll_fullscreen: B-roll video fills screen with captions on top
- pip: B-roll background + small body bottom-right corner
- text_cards: glass-morphism cards slide in (2-3 cards, eyebrow/headline/sub)
- website_overlay: website screenshot slides in from left
- stat_callout: big number springs in with label
- cta_closer: gradient CTA pill + URL typewriter effect

Available B-roll files: body_over_website.mp4
"""


def generate_script_and_config(
    topic: str,
    visual_personality: str = "competitive_dark",
    lang: str = "ar",
    duration_s: float = 30.0,
) -> dict:
    preset = VISUAL_PERSONALITIES.get(visual_personality, VISUAL_PERSONALITIES["competitive_dark"])
    lang_name = "Gulf Arabic (خليجي)" if lang == "ar" else "English"

    prompt = f"""You are an expert TikTok content strategist and video director for a sports AI brand called SportSync.

Your task: Generate a complete TikTok script AND a video engine configuration that tells Remotion exactly how to edit the video.

TOPIC: {topic}
LANGUAGE: {lang_name}
VISUAL PERSONALITY: {visual_personality} — {preset['vibe']}
TARGET DURATION: {duration_s:.0f} seconds
PLATFORM: TikTok / Instagram Reels
BRAND: SportSync AI — identifies your sport personality using AI in 3 minutes, free

REMOTION SYSTEM:
{REMOTION_STYLES}

SCRIPT RULES:
- Hook in first 3 seconds — must make viewer stop scrolling
- One clear idea, one CTA at the end
- Gulf Arabic: conversational, not formal
- 150-200 words max
- End with: "الرابط في البايو" or "جرب مجانا"

OUTPUT FORMAT — return ONLY this JSON, no explanation:
{{
  "script": {{
    "lines": [
      {{"text": "...", "start_s": 0.0, "end_s": 3.0, "type": "hook"}},
      {{"text": "...", "start_s": 3.0, "end_s": 8.0, "type": "problem"}},
      {{"text": "...", "start_s": 8.0, "end_s": 14.0, "type": "insight"}},
      {{"text": "...", "start_s": 14.0, "end_s": 20.0, "type": "solution"}},
      {{"text": "...", "start_s": 20.0, "end_s": 25.0, "type": "proof"}},
      {{"text": "...", "start_s": 25.0, "end_s": 30.0, "type": "cta"}}
    ],
    "full_text": "all lines joined",
    "caption": "TikTok caption with hashtags (Arabic)",
    "hook_type": "problem|question|stat|story"
  }},
  "engine_config": {{
    "audio_source": "clip_clean.mp4",
    "duration_s": {duration_s},
    "zoom_pulses": [[0,1],[2.5,1.055],[5,1],[7.5,1.06],[10,1],[12.5,1.055],[15,1],[17.5,1.06],[20,1],[22.5,1.055],[25,1],[27,1.05]],
    "shake_hits": [],
    "emphasis_words": [],
    "personality_labels": [],
    "flash_stats": [],
    "cta_start_s": 25.0,
    "preset": {{
      "zoom_intensity": {preset['zoom_intensity']},
      "shake_intensity": {preset['shake_intensity']},
      "scan_opacity_max": {preset['scan_opacity_max']},
      "accent_color": "{preset['accent_color']}",
      "label_color": "{preset['label_color']}",
      "bg": "{preset['bg']}"
    }},
    "director_note": "one sentence on creative direction"
  }}
}}

IMPORTANT for engine_config:
- shake_hits: timestamps (seconds) of the most impactful moments — 5-8 hits
- emphasis_words: Arabic words that should glow yellow when spoken — 8-12 words from the script
- personality_labels: [[start_s, "Label"], ...] — 4-6 personality type labels that appear briefly on screen
  Labels must be from: Competitive, Fighter, Strategic, Solo, Team Player, Leader, Creator, Explorer, Analyst, Performer
  Time them to appear during relevant parts of the script
- flash_stats: [[start_s, "text"], ...] — optional brief text flashes (stats, proof points)
- cta_start_s: when the CTA section begins (last 5-6 seconds)"""

    print(f"🤖 Script Agent thinking about: '{topic}'...")
    response = ask_claude(prompt)

    # Extract JSON
    start = response.find("{")
    end = response.rfind("}") + 1
    if start == -1:
        raise ValueError("No JSON in response")
    result = json.loads(response[start:end])
    return result


def save_outputs(result: dict, visual_personality: str):
    # Save engine_config.json → Remotion reads this at render time
    config_path = ROOT / "public" / "engine_config.json"
    config_path.write_text(json.dumps(result["engine_config"], ensure_ascii=False, indent=2))

    # Save script for reference
    script_path = ROOT / "public" / "current_script.json"
    script_path.write_text(json.dumps(result["script"], ensure_ascii=False, indent=2))

    return config_path, script_path


def print_script(result: dict):
    script = result["script"]
    config = result["engine_config"]

    print("\n" + "="*60)
    print("  📝 YOUR SCRIPT — Film this exactly")
    print("="*60)
    for line in script["lines"]:
        tag = f"[{line['start_s']:.0f}s–{line['end_s']:.0f}s] {line['type'].upper()}"
        print(f"\n{tag}")
        print(f"  {line['text']}")

    print("\n" + "="*60)
    print("  📱 TIKTOK CAPTION")
    print("="*60)
    print(f"\n{script['caption']}")

    print("\n" + "="*60)
    print("  🎬 ENGINE WILL DO AUTOMATICALLY")
    print("="*60)
    print(f"\n  Director note: {config.get('director_note', '')}")
    print(f"  Emphasis words: {', '.join(config.get('emphasis_words', []))}")
    labels = config.get('personality_labels', [])
    print(f"  Labels: {', '.join(f'{l[1]} @{l[0]:.0f}s' for l in labels)}")
    print(f"  Shake hits: {len(config.get('shake_hits', []))} moments")
    print(f"  CTA at: {config.get('cta_start_s', 25)}s")

    print("\n" + "="*60)
    print("  ✅ WHAT TO DO NEXT")
    print("="*60)
    print("""
  1. Film yourself saying the script above
  2. Save video to: public/clip_clean.mp4
  3. Run: python3 bin/generate_video.py --video public/clip_clean.mp4
  4. Watch the result in out/
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="Topic for the TikTok video")
    parser.add_argument("--personality", default="competitive_dark",
                        choices=list(VISUAL_PERSONALITIES.keys()))
    parser.add_argument("--lang", default="ar", choices=["ar", "en"])
    parser.add_argument("--duration", type=float, default=30.0)
    args = parser.parse_args()

    result = generate_script_and_config(args.topic, args.personality, args.lang, args.duration)
    config_path, script_path = save_outputs(result, args.personality)
    print_script(result)

    print(f"  engine_config.json saved → {config_path}")
    print(f"  current_script.json saved → {script_path}")
    print(f"\n  VisualPersonalityEngine is READY — film the script and drop the video in.\n")
