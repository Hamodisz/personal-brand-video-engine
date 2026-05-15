#!/usr/bin/env python3
"""
AI Video Director — Autonomous personal brand video pipeline.

Usage:
  python3 bin/ai_video_director.py --video ~/Downloads/myvideo.MOV
  python3 bin/ai_video_director.py --video path --dry-run
  python3 bin/ai_video_director.py --video path --storyboard-only
  python3 bin/ai_video_director.py --video path --regenerate-shot 2
  python3 bin/ai_video_director.py --video path --topic "why athletes plateau"
"""
import argparse, hashlib, json, os, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
PUBLIC = ROOT / "public"
BROLL_DIR = PUBLIC / "broll"
CACHE_FILE = PUBLIC / ".director_cache.json"
BRAIN_DIR = ROOT / "brain"
KNOWLEDGE_DIR = ROOT / "knowledge"

FFMPEG = os.path.expanduser("~/bin/ffmpeg")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")


# ──────────────────────────────────────────────
# STEP 1: PREP — color correct + portrait crop
# ──────────────────────────────────────────────

def prep_video(video_path: Path) -> Path:
    out = PUBLIC / "clip_clean.mp4"
    print("⟳ Color correcting video...")
    cmd = [
        FFMPEG, "-y", "-i", str(video_path),
        "-vf", (
            "zscale=transfer=linear:npl=100,format=gbrpf32le,zscale=primaries=bt709,"
            "tonemap=hable:desat=0.5,zscale=transfer=bt709:matrix=bt709:range=tv,format=yuv420p,"
            "scale=1080:-2,fps=30,eq=contrast=1.05:saturation=1.1"
        ),
        "-af", "afftdn=nf=-25,highpass=f=80,loudnorm=I=-14:TP=-2:LRA=7",
        "-c:v", "libx264", "-profile:v", "high", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✓ Saved to {out}")
    return out


# ──────────────────────────────────────────────
# STEP 2: BODY CUTOUT (cached)
# ──────────────────────────────────────────────

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}

def save_cache(data: dict):
    CACHE_FILE.write_text(json.dumps(data))

def build_body_cutout(video_path: Path):
    cache = load_cache()
    src_hash = _md5(video_path)

    if cache.get("source_hash") == src_hash and (PUBLIC / "body_cutout.webm").exists():
        print("✓ Body cutout cached — skipping rembg (saves ~8min)")
        return

    print("⟳ Building body cutout (this takes ~8 minutes)...")
    frames_dir = Path("/tmp/director_frames")
    cutout_dir = Path("/tmp/director_cutout")
    frames_dir.mkdir(exist_ok=True)
    cutout_dir.mkdir(exist_ok=True)

    # Extract frames
    subprocess.run([
        FFMPEG, "-y", "-i", str(video_path),
        str(frames_dir / "frame_%04d.png"),
    ], check=True, capture_output=True)

    # Remove background
    sys.path.insert(0, str(ROOT))
    from rembg import remove, new_session
    session = new_session("u2net")
    frame_files = sorted(frames_dir.glob("frame_*.png"))
    total = len(frame_files)
    print(f"  Removing background from {total} frames...")
    for i, fp in enumerate(frame_files):
        out_path = cutout_dir / fp.name
        if not out_path.exists():
            result = remove(fp.read_bytes(), session=session,
                            alpha_matting=True,
                            alpha_matting_foreground_threshold=230,
                            alpha_matting_background_threshold=20,
                            alpha_matting_erode_size=8)
            out_path.write_bytes(result)
        if (i + 1) % 30 == 0 or (i + 1) == total:
            print(f"  {i+1}/{total}")

    # Encode VP9 WebM with alpha (MUST use -auto-alt-ref 0)
    webm_out = PUBLIC / "body_cutout.webm"
    subprocess.run([
        FFMPEG, "-y", "-framerate", "30", "-i", str(cutout_dir / "frame_%04d.png"),
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
        "-b:v", "0", "-crf", "20", "-deadline", "good", "-cpu-used", "4",
        str(webm_out),
    ], check=True, capture_output=True)

    save_cache({"source_hash": src_hash})
    print(f"✓ Body cutout saved to {webm_out}")


# ──────────────────────────────────────────────
# STEP 3: TRANSCRIBE with Whisper
# ──────────────────────────────────────────────

def transcribe(video_path: Path) -> dict:
    transcript_path = PUBLIC / "transcript.json"
    if transcript_path.exists():
        print("✓ Transcript cached")
        return json.loads(transcript_path.read_text())

    print("⟳ Transcribing with Whisper (word-level)...")
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(str(video_path), word_timestamps=True)

    # Flatten to word list
    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start_s": round(w["start"], 3),
                "end_s": round(w["end"], 3),
            })

    transcript = {
        "text": result["text"],
        "segments": result["segments"],
        "words": words,
    }
    transcript_path.write_text(json.dumps(transcript, indent=2))
    print(f"✓ Transcript: {len(words)} words")
    return transcript


# ──────────────────────────────────────────────
# STEP 4: DIRECTOR AI — generates shot_plan.json
# ──────────────────────────────────────────────

def load_brain_context() -> str:
    parts = []

    core_path = BRAIN_DIR / "knowledge_core.md"
    if core_path.exists():
        core = core_path.read_text()[-3000:]
        parts.append(f"=== KNOWLEDGE CORE (distilled intelligence) ===\n{core}")

    live_path = BRAIN_DIR / "knowledge_live.md"
    if live_path.exists():
        live = live_path.read_text()[-1500:]
        parts.append(f"=== RECENT WINS (what's working now) ===\n{live}")

    strategy_path = BRAIN_DIR / "strategy.json"
    if strategy_path.exists():
        strategy = json.loads(strategy_path.read_text())
        cta = strategy.get("cta", "Take the Free Quiz → sportsync.ai/quiz")
        parts.append(f"=== CURRENT STRATEGY ===\nCTA: {cta}\nPriority: {strategy.get('priority_kpi', 'quiz completions')}")

    return "\n\n".join(parts) if parts else ""


DIRECTOR_SYSTEM = """You are a professional social media video editor specializing in personal brand TikToks.
You will receive a transcript and must produce a JSON shot plan.

HOOK LAWS:
- First 1.5s must stop the scroll — use body movement OR bold text, never both
- Hook must name a specific pain or named concept
- Never start with "I" — start with "Most people...", "The reason you...", "Nobody talks about..."
- If the first frame doesn't create curiosity → it fails

STYLE SELECTION RULES:
- Person makes a claim about other people's behavior → broll_fullscreen (SHOW it visually)
- Person mentions their product, quiz, or results → website_overlay
- Person lists 3+ related ideas → text_cards
- Person quotes a number or statistic → stat_callout
- Raw personal/emotional moment → talking_head
- Showing evidence while explaining → pip
- ALWAYS end with cta_closer

PACING:
- Min shot: 2.5s, max: 6s
- B-roll: fade in (handled automatically), hard cut out for urgency
- Text cards: stagger 1.5s between each card appearing
- CTA: needs 2.5s minimum after animation settles

B-ROLL SEARCH QUERY RULES:
- Search concrete visible actions, not abstract concepts
- "person stopping mid-run frustrated" NOT "running problems"
- Always include a setting: gym / outdoor / home / field
- Avoid generic stock: no trophies, no slow-motion jumping, no group high-fives

BRAND TONE (Mohammad Al-Saati / SportSync AI):
- Authority: "I built the AI that does X" — not "check out my product"
- Never pitch before second 10 — earn it with value first
- The quiz is the CTA; the pain is the hook; the science is the proof
- Tone: confident, matter-of-fact, slightly provocative

OUTPUT: Valid JSON only. Schema:
{
  "shots": [
    {
      "id": 1,
      "style": "talking_head|broll_fullscreen|pip|text_cards|stat_callout|website_overlay|cta_closer",
      "start_s": 0.0,
      "end_s": 3.0,
      "transition_out": "cut|crossfade_8|dip_black_10",
      "broll_query": "search query for Pexels (only for broll/pip shots)",
      "broll_loop": false,
      "cards": [{"eyebrow": "...", "headline": "...", "sub": "..."}],
      "stat": "8,000+",
      "stat_label": "sports analyzed",
      "stat_sub": "across 50 countries",
      "cta_text": "Take the Free Quiz →",
      "url": "sportsync.ai/quiz",
      "website_asset": "site_hero.png"
    }
  ]
}"""

def run_director(transcript: dict, topic_hint: str = "", regenerate_shot: int = None) -> dict:
    plan_path = PUBLIC / "shot_plan.json"
    if plan_path.exists() and regenerate_shot is None:
        print("✓ Shot plan cached (use --regenerate-shot N to redo a shot)")
        return json.loads(plan_path.read_text())

    brain_ctx = load_brain_context()
    duration_s = transcript["segments"][-1]["end"] if transcript.get("segments") else 16.2

    user_msg = f"""Video transcript (duration: {duration_s:.1f}s):
{transcript['text']}

{f'Topic hint: {topic_hint}' if topic_hint else ''}
{f'Brain context:{chr(10)}{brain_ctx}' if brain_ctx else ''}

Create a shot plan for this {duration_s:.1f}s video. The plan must cover the full duration exactly.
Output valid JSON only."""

    print("⟳ AI Creative Director is planning the video...")
    resp = _claude_call(DIRECTOR_SYSTEM, user_msg)
    # Extract JSON from response
    raw = resp.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    plan = json.loads(raw.strip())
    plan["audio_source"] = "clip_clean.mp4"
    plan["duration_s"] = duration_s
    plan["words"] = transcript.get("words", [])

    plan_path.write_text(json.dumps(plan, indent=2))
    print(f"✓ Shot plan: {len(plan['shots'])} shots")
    for s in plan["shots"]:
        print(f"  [{s['id']}] {s['style']:18s} {s['start_s']:.1f}s–{s['end_s']:.1f}s  {s.get('broll_query','')}")
    return plan


# ──────────────────────────────────────────────
# STEP 5: ASSET SOURCING — Pexels B-roll
# ──────────────────────────────────────────────

def download_broll(plan: dict):
    BROLL_DIR.mkdir(exist_ok=True)
    broll_shots = [s for s in plan["shots"] if s["style"] in ("broll_fullscreen", "pip") and s.get("broll_query")]

    for shot in broll_shots:
        broll_file = BROLL_DIR / f"shot{shot['id']}.mp4"
        if broll_file.exists():
            shot["broll_file"] = f"broll/shot{shot['id']}.mp4"
            print(f"✓ B-roll shot {shot['id']} cached")
            continue

        query = shot["broll_query"]
        print(f"⟳ Fetching B-roll for shot {shot['id']}: \"{query}\"")
        video_url = _pexels_search(query)
        if not video_url:
            print(f"  ⚠ No Pexels result for \"{query}\" — shot will use talking_head fallback")
            shot["style"] = "talking_head"
            continue

        print(f"  Downloading {video_url[:60]}...")
        urllib.request.urlretrieve(video_url, broll_file)
        shot["broll_file"] = f"broll/shot{shot['id']}.mp4"
        print(f"  ✓ Saved to {broll_file}")

    # Update plan with broll_file paths
    (PUBLIC / "shot_plan.json").write_text(json.dumps(plan, indent=2))


def _pexels_search(query: str) -> str:
    if not PEXELS_KEY:
        print("  ⚠ PEXELS_API_KEY not set — skipping B-roll download")
        return ""
    url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&per_page=5&orientation=portrait&size=medium"
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    videos = data.get("videos", [])
    if not videos:
        return ""
    # Pick first video, best quality portrait file
    for vid in videos:
        for f in vid.get("video_files", []):
            if f.get("quality") in ("hd", "sd") and f.get("height", 0) >= 720:
                return f["link"]
    return videos[0]["video_files"][0]["link"] if videos[0]["video_files"] else ""


# ──────────────────────────────────────────────
# STEP 6: STORYBOARD — one frame per shot
# ──────────────────────────────────────────────

def render_storyboard(plan: dict):
    storyboard_dir = Path("/tmp/storyboard")
    storyboard_dir.mkdir(exist_ok=True)
    fps = 30
    print("⟳ Rendering storyboard (1 frame per shot)...")
    frames = []
    for shot in plan["shots"]:
        mid_s = (shot["start_s"] + shot["end_s"]) / 2
        mid_frame = int(mid_s * fps)
        out_path = storyboard_dir / f"shot{shot['id']}_{shot['style']}.png"
        cmd = [
            "npx", "remotion", "still", "src/index.ts", "SmartEdit",
            f"--frame={mid_frame}", f"--output={out_path}",
        ]
        print(f"  Shot {shot['id']} ({shot['style']}) @ {mid_s:.1f}s...")
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True)
        if result.returncode == 0:
            frames.append(str(out_path))
        else:
            print(f"  ⚠ Frame render failed for shot {shot['id']}")

    print(f"\n✓ Storyboard: {len(frames)} frames saved to /tmp/storyboard/")
    if frames:
        subprocess.run(["open", "/tmp/storyboard/"], check=False)
    return frames


# ──────────────────────────────────────────────
# STEP 7: RENDER
# ──────────────────────────────────────────────

def render_final(plan: dict) -> Path:
    import time
    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    duration_s = plan["duration_s"]
    fps = 30
    total_frames = int(duration_s * fps)

    # Update Root.tsx duration to match actual video length
    _patch_smartedit_duration(total_frames)

    ts = int(time.time())
    out_path = out_dir / f"{ts}_smart_edit.mp4"

    print(f"\n⟳ Rendering final video ({duration_s:.1f}s, {total_frames} frames)...")
    cmd = [
        "npx", "remotion", "render", "src/index.ts", "SmartEdit",
        f"--output={out_path}",
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    print(f"\n✓ Final video: {out_path}")
    subprocess.run(["open", str(out_path)], check=False)
    return out_path


def _patch_smartedit_duration(frames: int):
    root_tsx = ROOT / "src" / "Root.tsx"
    content = root_tsx.read_text()
    import re
    content = re.sub(
        r'(id="SmartEdit"[^>]+durationInFrames=\{)\d+(\})',
        rf'\g<1>{frames}\2',
        content,
    )
    root_tsx.write_text(content)


# ──────────────────────────────────────────────
# CLAUDE API HELPER
# ──────────────────────────────────────────────

def _claude_call(system: str, user: str) -> str:
    import urllib.parse
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_KEY.strip(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    import urllib.parse

    parser = argparse.ArgumentParser(description="AI Video Director")
    parser.add_argument("--video", required=True, help="Path to raw iPhone video (.MOV or .mp4)")
    parser.add_argument("--topic", default="", help="Optional topic hint for better B-roll queries")
    parser.add_argument("--dry-run", action="store_true", help="Transcript + shot plan only, no render")
    parser.add_argument("--storyboard-only", action="store_true", help="One frame per shot, no full render")
    parser.add_argument("--regenerate-shot", type=int, default=None, help="Re-generate shot N only")
    args = parser.parse_args()

    video_path = Path(args.video).expanduser()
    if not video_path.exists():
        print(f"Error: {video_path} not found")
        sys.exit(1)

    print(f"\n🎬 AI Video Director — {video_path.name}\n")

    # Step 1: Prep (skip if clip_clean.mp4 already exists for same source)
    if not (PUBLIC / "clip_clean.mp4").exists():
        prep_video(video_path)
    else:
        print("✓ clip_clean.mp4 exists")

    # Step 2: Body cutout (cached)
    build_body_cutout(PUBLIC / "clip_clean.mp4")

    # Step 3: Transcribe
    transcript = transcribe(PUBLIC / "clip_clean.mp4")

    # Step 4: Director AI
    plan = run_director(transcript, topic_hint=args.topic, regenerate_shot=args.regenerate_shot)

    if args.dry_run:
        print("\n[DRY RUN] Shot plan:")
        print(json.dumps(plan, indent=2))
        return

    # Step 5: Download B-roll
    download_broll(plan)

    if args.storyboard_only:
        render_storyboard(plan)
        return

    # Step 6: Storyboard preview
    render_storyboard(plan)
    print("\nReview the storyboard above. Starting full render in 5s... (Ctrl+C to cancel)")
    import time; time.sleep(5)

    # Step 7: Render
    render_final(plan)


if __name__ == "__main__":
    main()
