#!/usr/bin/env python3
"""Remove background from video frames using rembg AI."""
import os
import sys
from pathlib import Path
from rembg import remove, new_session

INPUT_DIR  = Path("/tmp/frames_color")
OUTPUT_DIR = Path("/tmp/cutout")
OUTPUT_DIR.mkdir(exist_ok=True)

frames = sorted(INPUT_DIR.glob("frame_*.png"))
total  = len(frames)
print(f"Processing {total} frames...")

session = new_session("u2net_human_seg")  # optimised for human body cutout

for i, frame_path in enumerate(frames):
    out_path = OUTPUT_DIR / frame_path.name
    if out_path.exists():
        continue
    with open(frame_path, "rb") as f:
        inp = f.read()
    result = remove(inp, session=session, alpha_matting=True,
                    alpha_matting_foreground_threshold=230,
                    alpha_matting_background_threshold=20,
                    alpha_matting_erode_size=8)
    with open(out_path, "wb") as f:
        f.write(result)
    if (i + 1) % 10 == 0 or (i + 1) == total:
        print(f"  {i+1}/{total} done", flush=True)

print(f"All frames saved to {OUTPUT_DIR}")
