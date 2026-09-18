#!/usr/bin/env python3
"""Rough Cut: deterministic compiler. Turns an approved edit_plan.json into an
actual cut video + a Remotion-ready shot_plan.json on the new timeline. No AI
here -- the LLM already decided WHAT; this executes HOW (spec's own principle
that deterministic tools execute HOW, the LLM decides WHAT).

Usage:
    python3 bin/rough_cut.py session_001 s1 [--preview]
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import sessions as S
from lib.media import load_summarize_cut

ROOT = Path(__file__).parent.parent
PUBLIC = ROOT / "public"


def build_ffmpeg_segments(edit_plan):
    segs = []
    for d in edit_plan:
        if d["decision"] == "keep":
            segs.append((d["start_s"], d["end_s"]))
        elif d["decision"] == "trim":
            segs.append((d["start_s"], d["trim_end_s"]))
    return segs


def compile_shot_plan(edit_plan, audio_source):
    shots = []
    t = 0.0
    for i, d in enumerate(edit_plan):
        if d["decision"] not in ("keep", "trim"):
            continue
        dur = d["trim_end_s"] - d["start_s"] if d["decision"] == "trim" else d["end_s"] - d["start_s"]
        shots.append({
            "id": i + 1, "style": "talking_head",
            "start_s": round(t, 2), "end_s": round(t + dur, 2),
            "transition_out": "cut", "sfx": [],
        })
        t += dur
    return {"audio_source": audio_source, "duration_s": round(t, 2), "shots": shots}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    parser.add_argument("story_id")
    parser.add_argument("--preview", action="store_true", help="copy into public/ for a Remotion still check")
    args = parser.parse_args()

    out_dir = S.story_dir(args.session_id, args.story_id)
    edit_plan = S.load_json(out_dir / "edit_plan.json")
    meta = S.load_meta(args.session_id)

    sc = load_summarize_cut()
    src = Path(meta["normalized_video_path"])
    src_w, src_h = sc.get_resolution(src)

    ffmpeg_segments = build_ffmpeg_segments(edit_plan)
    if not ffmpeg_segments:
        print("No keep/trim decisions -- nothing to cut.")
        sys.exit(1)

    dest = out_dir / "rough_cut.mp4"
    sc.cut_and_crop(src, dest, ffmpeg_segments, crop="none", src_w=src_w, src_h=src_h)

    print("⟳ Transcribing rough cut at word level for caption sync...")
    import whisper
    model = whisper.load_model("large-v3")
    result = model.transcribe(str(dest), word_timestamps=True)
    captions = [
        {"text": w["word"], "startMs": round(w["start"] * 1000), "endMs": round(w["end"] * 1000),
         "timestampMs": round(w["start"] * 1000), "confidence": round(w.get("probability", 0.9), 3)}
        for seg in result["segments"] for w in seg.get("words", [])
    ]
    S.save_json(out_dir / "captions.json", captions)

    shot_plan = compile_shot_plan(edit_plan, "rough_cut.mp4")
    S.save_json(out_dir / "shot_plan.json", shot_plan)
    S.update_status(args.session_id, "rough_cut")

    print(f"✓ Rough cut: {shot_plan['duration_s']:.0f}s, {len(shot_plan['shots'])} shots -> {dest}")

    if args.preview:
        targets = ["clip_clean.mp4", "captions.json", "shot_plan.json"]
        existing = [t for t in targets if (PUBLIC / t).exists()]
        if existing:
            backup_dir = PUBLIC / ".session_preview_backup" / time.strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)
            for t in existing:
                shutil.move(str(PUBLIC / t), str(backup_dir / t))
            print(f"  (backed up existing public/{{{', '.join(existing)}}} -> {backup_dir} first "
                  f"-- this preview step previously overwrote real project files with no backup)")
        print("⟳ Copying into public/ for a Remotion still check (per this repo's CLAUDE.md rule)...")
        shutil.copy(dest, PUBLIC / "clip_clean.mp4")
        shutil.copy(out_dir / "captions.json", PUBLIC / "captions.json")
        shutil.copy(out_dir / "shot_plan.json", PUBLIC / "shot_plan.json")
        mid_frame = int(shot_plan["duration_s"] * 15)  # ~30fps, midpoint
        print(f"  Run: npx remotion still src/index.ts SmartEdit --frame={mid_frame} --output=/tmp/preview.png")
        print("  Then open /tmp/preview.png and verify it looks correct BEFORE rendering the full video.")


if __name__ == "__main__":
    main()
