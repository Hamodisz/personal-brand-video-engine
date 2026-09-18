#!/usr/bin/env python3
"""Ingest a raw session recording: multi-source signal extraction, merged into
one timeline BEFORE any event/story reasoning happens. Screen/OCR is the
primary source for a silent screen-only recording; audio, git, and Claude
Code session-log activity are additional first-class sources whenever they're
available -- none of them required, none of them assumed.

Usage:
    python3 bin/session_ingest.py --video "/path/to/recording.mov" --note "context" \
        --repo ~/Desktop/personal-brand --repo ~/Desktop/SportSyncAI-Main \
        [--started-at 2026-09-17T19:19:03Z] [--scene-threshold 0.4]

If --started-at is omitted, the recording's own container creation_time tag
is used (screen recordings via QuickTime/ReplayKit embed this) -- verified
present and accurate on a real test recording. Without a resolvable wall-clock
start, git/Claude-Code-log correlation is skipped (nothing to align against)
but OCR/scene-detection still run.
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import sessions as S
from lib import signals as sig
from lib.media import load_summarize_cut, get_creation_time, get_duration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--note", default="", help="one-line context: what this session was about")
    parser.add_argument("--repo", action="append", default=[],
                         help="repo path to correlate git + Claude Code session-log activity from; repeatable")
    parser.add_argument("--started-at", default=None,
                         help="ISO wall-clock start of the recording; falls back to the video's own creation_time tag")
    parser.add_argument("--scene-threshold", type=float, default=0.1,
                         help="ffmpeg hard-scene-change sensitivity (supplementary; see fixed-interval sampling for the reliable floor)")
    parser.add_argument("--sample-interval", type=float, default=3.0,
                         help="fixed-interval OCR sampling in seconds -- the reliable floor for text-heavy, mostly-static screens")
    parser.add_argument("--whisper-model", default="large-v3")
    parser.add_argument("--lang", default=None, help="Whisper language hint, e.g. 'ar' or 'en' -- only used if audio has signal")
    args = parser.parse_args()

    video_path = Path(args.video).expanduser()
    if not video_path.exists():
        print(f"Error: {video_path} not found")
        sys.exit(1)

    sc = load_summarize_cut()

    session_id = S.next_session_id()
    sdir = S.new_session_dir(session_id)
    print(f"→ {session_id}: {video_path.name}")

    wall_start = None
    if args.started_at:
        wall_start = datetime.fromisoformat(args.started_at.replace("Z", "+00:00"))
    else:
        wall_start = get_creation_time(video_path)
        if wall_start:
            print(f"  (using recording's own creation_time tag as wall-clock start: {wall_start.isoformat()})")
    if not wall_start and args.repo:
        print("  ⚠ No wall-clock start available (no --started-at, no creation_time tag) -- "
              "git/Claude-Code-log correlation will be skipped even though --repo was given.")

    print("⟳ Normalizing (constant fps, capped resolution)...")
    normalized_path, w, h = sc.normalize_source(video_path)
    dest = sdir / "normalized.mp4"
    normalized_path.replace(dest)
    print(f"✓ Normalized -> {dest} ({w}x{h})")

    duration_s = get_duration(dest)

    has_audio = sig.audio_has_signal(dest)
    audio_stream = []
    if has_audio:
        print("⟳ Real audio detected -- transcribing (segment-level)...")
        segments = sc.transcribe(dest, args.whisper_model, args.lang)
        S.save_json(sdir / "transcript.json", segments)
        audio_stream = [{"t": s["start_s"], "source": "audio", "data": s["text"]} for s in segments]
        print(f"✓ Transcript: {len(segments)} segments")
    else:
        print("  (no meaningful audio signal -- skipping transcription, screen/OCR carries the session)")

    print(f"⟳ Detecting hard scene changes (threshold={args.scene_threshold})...")
    scene_times = sig.detect_scene_changes(dest, threshold=args.scene_threshold)
    fixed_times = sig.fixed_interval_samples(duration_s, interval=args.sample_interval)
    sample_times = sorted({round(t, 1) for t in (scene_times + fixed_times)})
    print(f"✓ {len(scene_times)} hard scene changes + {len(fixed_times)} fixed-interval samples "
          f"= {len(sample_times)} frames to OCR")
    print("⟳ Running OCR on sampled frames...")
    ocr_stream = sig.ocr_signals(dest, sample_times)
    print(f"✓ OCR produced {len(ocr_stream)} non-empty text signals")

    git_stream, terminal_stream = [], []
    if wall_start and args.repo:
        wall_end = wall_start + timedelta(seconds=duration_s)
        for repo in args.repo:
            repo_path = Path(repo).expanduser()
            found = sig.git_signals(repo_path, wall_start, wall_end)
            git_stream += found
            print(f"  git[{repo_path.name}]: {len(found)} commits in window")
        terminal_stream = sig.claude_code_signals([Path(r).expanduser() for r in args.repo], wall_start, wall_end)
        print(f"  Claude Code session logs: {len(terminal_stream)} entries in window")

    timeline = sig.merge_timeline(audio_stream, ocr_stream, git_stream, terminal_stream)
    S.save_json(sdir / "timeline.json", timeline)

    meta = {
        "session_id": session_id,
        "slug": S.slugify(args.note or video_path.stem),
        "recorded_at": S.now_iso(),
        "raw_video_path": str(video_path),
        "normalized_video_path": str(dest),
        "topic_note": args.note,
        "duration_s": duration_s,
        "wall_clock_start": wall_start.isoformat() if wall_start else None,
        "repos": args.repo,
        "has_audio": has_audio,
        "signals_used": sorted({e["source"] for e in timeline}),
        "status": "ingested",
    }
    S.save_json(sdir / "meta.json", meta)
    S.update_status(session_id, "signals_extracted")

    print(f"✓ {session_id}: {len(timeline)} merged timeline entries ({', '.join(meta['signals_used']) or 'none'})")
    print(f"  Next: python3 bin/event_miner.py {session_id}")


if __name__ == "__main__":
    main()
