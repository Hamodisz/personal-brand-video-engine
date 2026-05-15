#!/usr/bin/env python3
"""
grab_broll.py — paste any video URL, get a ready-to-use portrait B-roll

Usage:
  python3 bin/grab_broll.py <URL>
  python3 bin/grab_broll.py <URL> --slot broll2   # saves as sport_broll2.mp4
  python3 bin/grab_broll.py <URL> --no-plan       # skip shot_plan.json update

Supports: Pexels, Pixabay, YouTube, Vimeo, Instagram, TikTok, 1000+ sites
"""
import sys
import os
import json
import subprocess
import tempfile
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PUBLIC = PROJECT_ROOT / "public"
FFMPEG = Path.home() / "bin" / "ffmpeg"
YTDLP = Path.home() / "Library/Python/3.9/bin/yt-dlp"
SHOT_PLAN = PUBLIC / "shot_plan.json"


def detect_orientation(video_path):
    """Returns (width, height) of the video."""
    result = subprocess.run(
        [str(FFMPEG), "-i", str(video_path)],
        capture_output=True, text=True
    )
    output = result.stderr
    for line in output.splitlines():
        if "Video:" in line and "x" in line:
            parts = line.split()
            for p in parts:
                if "x" in p and p.replace("x", "").replace(",", "").replace(".", "").isdigit():
                    dims = p.strip(",").split("x")
                    if len(dims) == 2:
                        try:
                            return int(dims[0]), int(dims[1])
                        except ValueError:
                            continue
    return 1920, 1080  # assume landscape


def download(url, tmp_dir):
    print(f"Downloading: {url}")
    out_template = os.path.join(tmp_dir, "source.%(ext)s")
    cmd = [
        str(YTDLP),
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", out_template,
        "--no-playlist",
        url
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("ERROR: Download failed. Check the URL and try again.")
        sys.exit(1)

    # Find the downloaded file
    for f in Path(tmp_dir).glob("source.*"):
        return f
    print("ERROR: Downloaded file not found.")
    sys.exit(1)


def encode_portrait(src, dst):
    """Re-encode to 1080x1920 portrait, cropping landscape if needed."""
    w, h = detect_orientation(src)
    print(f"Source: {w}x{h} → encoding to 1080x1920 portrait...")

    if w > h:
        # Landscape source — crop center column to 9:16
        vf = "crop=ih*9/16:ih,scale=1080:1920:flags=lanczos,setsar=1"
    elif w == h:
        # Square — add bars or crop
        vf = "scale=1080:1080:flags=lanczos,pad=1080:1920:0:(oh-iw)/2:color=black,setsar=1"
    else:
        # Already portrait — just scale
        vf = "scale=1080:1920:flags=lanczos,setsar=1"

    cmd = [
        str(FFMPEG), "-y",
        "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-b:a", "128k",
        "-movflags", "+faststart",
        str(dst)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: ffmpeg encode failed:")
        print(result.stderr[-2000:])
        sys.exit(1)


def update_shot_plan(broll_filename):
    """Add or update PiP shot in shot_plan.json using this broll."""
    if not SHOT_PLAN.exists():
        print("No shot_plan.json found — skipping plan update.")
        return

    with open(SHOT_PLAN) as f:
        plan = json.load(f)

    shots = plan.get("shots", [])
    duration = plan.get("duration_s", 29.6)

    # Remove any existing pip shots using this broll
    shots = [s for s in shots if not (s.get("style") == "pip" and s.get("broll_file") == broll_filename)]

    # Add PiP at start
    pip_shot = {
        "id": 0,
        "style": "pip",
        "start_s": 0.0,
        "end_s": min(15.0, duration),
        "broll_file": broll_filename,
        "broll_loop": True
    }
    shots.insert(0, pip_shot)
    plan["shots"] = shots

    with open(SHOT_PLAN, "w") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"shot_plan.json updated — PiP shot added with {broll_filename}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Any video URL (Pexels, YouTube, Pixabay, etc.)")
    parser.add_argument("--slot", default="sport_broll", help="Output slot name (default: sport_broll)")
    parser.add_argument("--no-plan", action="store_true", help="Skip shot_plan.json update")
    args = parser.parse_args()

    output_filename = f"{args.slot}.mp4"
    output_path = PUBLIC / output_filename

    with tempfile.TemporaryDirectory() as tmp:
        src = download(args.url, tmp)
        encode_portrait(src, output_path)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"\nDONE: {output_path} ({size_mb:.1f}MB)")

    if not args.no_plan:
        update_shot_plan(output_filename)

    print(f"\nReady. Run this to preview:")
    print(f"  npx remotion still src/index.ts SmartEdit --frame=60 --output=/tmp/broll_test.png && open /tmp/broll_test.png")


if __name__ == "__main__":
    main()
