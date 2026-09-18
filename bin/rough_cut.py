#!/usr/bin/env python3
"""Rough Cut: deterministic compiler. Turns an approved edit_plan.json into an
actual cut video + a Remotion-ready shot_plan.json on the new timeline. No AI
here -- the LLM already decided WHAT; this executes HOW (spec's own principle
that deterministic tools execute HOW, the LLM decides WHAT).

Handles per-segment `speed` (real feature: trim+setpts+concat, not deferred)
and works whether or not the session has real audio.

Usage:
    python3 bin/rough_cut.py session_001 s1 [--preview]
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import sessions as S
from lib.media import load_summarize_cut, resolve_ffmpeg

ROOT = Path(__file__).parent.parent
PUBLIC = ROOT / "public"


def _atempo_chain(speed: float) -> str:
    """atempo only accepts [0.5, 2.0] per instance -- chain for out-of-range speeds."""
    if not speed or abs(speed - 1.0) < 1e-6:
        return ""
    parts, remaining = [], speed
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    if abs(remaining - 1.0) > 1e-6:
        parts.append(f"atempo={remaining:.4f}")
    return ("," + ",".join(parts)) if parts else ""


def kept_decisions(edit_plan):
    return [d for d in edit_plan if d["decision"] in ("keep", "trim")]


def decision_span(d):
    end = d["trim_end_s"] if d["decision"] == "trim" else d["end_s"]
    return d["start_s"], end


def cut_with_speed_segments(src: Path, dest: Path, decisions: list, has_audio: bool, fps: int = 30) -> float:
    """New, real logic (not in summarize_cut.py): per-segment trim+setpts+concat
    so each kept range can have its own playback speed, then muxed back together."""
    ffmpeg = resolve_ffmpeg()
    v_parts, a_parts, concat_pairs = [], [], []
    expected_duration = 0.0
    for i, d in enumerate(decisions):
        start, end = decision_span(d)
        speed = d.get("speed", 1.0) or 1.0
        expected_duration += (end - start) / speed
        v_parts.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=(PTS-STARTPTS)/{speed:.3f}[v{i}]")
        if has_audio:
            a_parts.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS{_atempo_chain(speed)}[a{i}]")
            concat_pairs.append(f"[v{i}][a{i}]")
        else:
            concat_pairs.append(f"[v{i}]")

    n = len(decisions)
    filter_complex = ";".join(v_parts)
    if has_audio:
        filter_complex += ";" + ";".join(a_parts)
        filter_complex += f";{''.join(concat_pairs)}concat=n={n}:v=1:a=1[vout][aout]"
        maps = ["-map", "[vout]", "-map", "[aout]"]
    else:
        filter_complex += f";{''.join(concat_pairs)}concat=n={n}:v=1:a=0[vout]"
        maps = ["-map", "[vout]"]

    cmd = [ffmpeg, "-y", "-i", str(src), "-filter_complex", filter_complex, *maps,
           "-c:v", "libx264", "-profile:v", "high", "-crf", "20", "-preset", "fast",
           "-g", str(fps), "-keyint_min", str(fps), "-sc_threshold", "0",
           "-pix_fmt", "yuv420p"]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-t", f"{expected_duration:.3f}", "-movflags", "+faststart", str(dest)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg cut failed:\n{r.stderr[-3000:]}")
    return expected_duration


def patch_smartedit_duration(frames: int) -> None:
    """SmartEdit's durationInFrames in Root.tsx is scratch state, patched per
    render -- same regex ai_video_director.py already uses for this, reused
    here rather than reinvented."""
    root_tsx = ROOT / "src" / "Root.tsx"
    content = root_tsx.read_text()
    content = re.sub(r'(id="SmartEdit"[^>]+durationInFrames=\{)\d+(\})', rf"\g<1>{frames}\2", content)
    root_tsx.write_text(content)


def compile_shot_plan(decisions: list, audio_source: str) -> dict:
    shots = []
    t = 0.0
    for i, d in enumerate(decisions):
        start, end = decision_span(d)
        speed = d.get("speed", 1.0) or 1.0
        dur = (end - start) / speed
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
    has_audio = meta.get("has_audio", False)

    decisions = kept_decisions(edit_plan)
    if not decisions:
        print("No keep/trim decisions -- nothing to cut.")
        sys.exit(1)

    sc = load_summarize_cut()
    src = Path(meta["normalized_video_path"])

    dest = out_dir / "rough_cut.mp4"
    expected_duration = cut_with_speed_segments(src, dest, decisions, has_audio)
    sc.verify_output_duration(dest, expected_duration)

    if has_audio:
        print("⟳ Transcribing rough cut at word level for caption sync...")
        import whisper
        model = whisper.load_model("large-v3")
        result = model.transcribe(str(dest), word_timestamps=True)
        captions = [
            {"text": w["word"], "startMs": round(w["start"] * 1000), "endMs": round(w["end"] * 1000),
             "timestampMs": round(w["start"] * 1000), "confidence": round(w.get("probability", 0.9), 3)}
            for seg in result["segments"] for w in seg.get("words", [])
        ]
    else:
        print("  (no audio -- skipping caption transcription)")
        captions = []
    S.save_json(out_dir / "captions.json", captions)

    shot_plan = compile_shot_plan(decisions, "rough_cut.mp4")
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
            print(f"  (backed up existing public/{{{', '.join(existing)}}} -> {backup_dir} first)")
        print("⟳ Copying into public/ for a Remotion still check (per this repo's CLAUDE.md rule)...")
        shutil.copy(dest, PUBLIC / "clip_clean.mp4")
        shutil.copy(out_dir / "captions.json", PUBLIC / "captions.json")
        shutil.copy(out_dir / "shot_plan.json", PUBLIC / "shot_plan.json")
        total_frames = int(shot_plan["duration_s"] * 30) + 30
        patch_smartedit_duration(total_frames)
        print(f"  (patched Root.tsx SmartEdit durationInFrames -> {total_frames})")
        mid_frame = int(shot_plan["duration_s"] * 15)
        print(f"  Run: npx remotion still src/index.ts SmartEdit --frame={mid_frame} --output=/tmp/preview.png")
        print("  Then open /tmp/preview.png and verify it looks correct BEFORE rendering the full video.")


if __name__ == "__main__":
    main()
