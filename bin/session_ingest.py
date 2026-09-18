#!/usr/bin/env python3
"""Ingest a raw session recording: normalize to constant fps (cached once,
since re-encoding a multi-hour video is expensive — see summarize_cut.py's
normalize_source), transcribe at segment level, and create
sessions/<id>/{meta.json, transcript.json, normalized.mp4}.

Usage:
    python3 bin/session_ingest.py --video "/path/to/recording.mov" --note "context"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import sessions as S
from lib.media import load_summarize_cut


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--note", default="", help="one-line context: what this session was about")
    parser.add_argument("--whisper-model", default="large-v3")
    parser.add_argument("--lang", default=None, help="Whisper language hint, e.g. 'ar' or 'en'")
    args = parser.parse_args()

    video_path = Path(args.video).expanduser()
    if not video_path.exists():
        print(f"Error: {video_path} not found")
        sys.exit(1)

    sc = load_summarize_cut()

    session_id = S.next_session_id()
    sdir = S.new_session_dir(session_id)
    print(f"→ {session_id}: {video_path.name}")

    print("⟳ Normalizing (constant fps, capped resolution)...")
    normalized_path, w, h = sc.normalize_source(video_path)
    dest = sdir / "normalized.mp4"
    normalized_path.replace(dest)
    print(f"✓ Normalized -> {dest} ({w}x{h})")

    segments = sc.transcribe(dest, args.whisper_model, args.lang)
    S.save_json(sdir / "transcript.json", segments)

    duration_s = segments[-1]["end_s"] if segments else 0.0
    meta = {
        "session_id": session_id,
        "slug": S.slugify(args.note or video_path.stem),
        "recorded_at": S.now_iso(),
        "raw_video_path": str(video_path),
        "normalized_video_path": str(dest),
        "topic_note": args.note,
        "duration_s": duration_s,
        "status": "ingested",
    }
    S.save_json(sdir / "meta.json", meta)
    S.update_status(session_id, "transcribed")

    print(f"✓ {session_id}: {len(segments)} segments, {duration_s:.0f}s total")
    print(f"  Next: python3 bin/event_miner.py {session_id}")


if __name__ == "__main__":
    main()
