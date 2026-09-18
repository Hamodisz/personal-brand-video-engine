"""Multi-source signal extraction: screen/OCR, git, Claude Code session logs,
and an audio presence check -- merged into one timeline BEFORE any event/story
reasoning happens. Audio is one signal among several, never required.

Verified against a real recording+session before being written (not guessed):
- easyocr is installed and importable; the `tesseract` binary is not, and
  Homebrew isn't available to add it -- easyocr needs no external binary.
- Claude Code session logs live at ~/.claude/projects/<slugified-cwd>/*.jsonl,
  one line per event, with real ISO timestamps and tool_use/tool_result pairs.
  Cross-checked a real recording's session log against the actual video and
  it caught a real narrative error that two rounds of manual frame-reading
  both missed (an unresolved anomaly at the very end, not a clean success).
"""
import glob
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import media

MAX_OCR_FRAMES = 200  # cost cap; a much longer recording needs smarter sampling, not a bigger cap
_easyocr_reader = None


def detect_scene_changes(video_path, threshold: float = 0.1, ffmpeg: Optional[str] = None) -> list:
    """Timestamps where the screen visually changed a lot, via ffmpeg's scene
    filter -- catches genuine hard cuts (switching apps/windows). Tested against
    a real 6:32 IDE screen recording: scene scores were heavily skewed near zero
    (median 1.3e-05 across 11,782 frames; only ~20 exceeded 0.1) because this
    metric measures whole-frame difference, and a mostly-static dark UI with a
    few lines of text changing barely moves it -- no threshold fixes that, it's
    the wrong primary tool for this content. Kept as a supplementary signal for
    real hard cuts; fixed_interval_samples() is the reliable floor."""
    ffmpeg = ffmpeg or media.resolve_ffmpeg()
    cmd = [ffmpeg, "-i", str(video_path), "-vf", f"select='gt(scene,{threshold})',showinfo",
           "-an", "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True).stderr
    times = sorted({round(float(m), 2) for m in re.findall(r"pts_time:([\d.]+)", out)})
    return times


def fixed_interval_samples(duration_s: float, interval: float = 3.0) -> list:
    """The reliable floor for sampling a mostly-static, text-heavy screen
    recording -- catches gradual/incremental changes (typing, scrolling, small
    UI updates) that whole-frame scene-difference scoring misses entirely."""
    n = int(duration_s // interval) + 1
    return [round(i * interval, 2) for i in range(n) if i * interval <= duration_s]


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        print("  (loading easyocr model, one-time cost per process)")
        _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _easyocr_reader


def ocr_frame_at(video_path, t: float, ffmpeg: Optional[str] = None) -> str:
    ffmpeg = ffmpeg or media.resolve_ffmpeg()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
        subprocess.run([ffmpeg, "-y", "-ss", f"{t:.3f}", "-i", str(video_path),
                        "-frames:v", "1", tmp.name], capture_output=True, check=True)
        reader = _get_easyocr_reader()
        results = reader.readtext(tmp.name, detail=0, paragraph=True)
        return " ".join(str(r) for r in results).strip()


def ocr_signals(video_path, timestamps: list, ffmpeg: Optional[str] = None) -> list:
    if len(timestamps) > MAX_OCR_FRAMES:
        print(f"  ⚠ {len(timestamps)} scene changes exceeds the {MAX_OCR_FRAMES}-frame OCR cap "
              f"-- sampling evenly down to {MAX_OCR_FRAMES}. Revisit sampling strategy for longer recordings.")
        step = len(timestamps) / MAX_OCR_FRAMES
        timestamps = [timestamps[int(i * step)] for i in range(MAX_OCR_FRAMES)]
    signals = []
    for i, t in enumerate(timestamps):
        text = ocr_frame_at(video_path, t, ffmpeg)
        if text:
            signals.append({"t": t, "source": "ocr", "data": text})
        if (i + 1) % 10 == 0:
            print(f"  OCR: {i + 1}/{len(timestamps)} frames")
    return signals


def audio_has_signal(video_path, ffmpeg: Optional[str] = None, mean_db_threshold: float = -45.0) -> bool:
    """Quick loudness check -- only transcribe if there's real signal, never
    run Whisper against a near-silent track (this exact recording's original
    audio was ~2kbps/near-silent, confirmed earlier in this project)."""
    ffmpeg = ffmpeg or media.resolve_ffmpeg()
    out = subprocess.run([ffmpeg, "-i", str(video_path), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", out)
    return bool(m) and float(m.group(1)) > mean_db_threshold


def git_signals(repo_path, start_dt: datetime, end_dt: datetime) -> list:
    """Real commit timestamps + diffstat within the recording's real wall-clock
    window -- ground truth, no OCR guessing needed for 'what changed'."""
    cmd = ["git", "-C", str(repo_path), "log", "--all",
           f"--since={start_dt.isoformat()}", f"--until={end_dt.isoformat()}",
           "--format=@@%H|%aI|%s", "--shortstat"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    signals = []
    entry_lines = [l for l in out.splitlines()]
    i = 0
    while i < len(entry_lines):
        line = entry_lines[i]
        if line.startswith("@@"):
            h, iso, subject = line[2:].split("|", 2)
            commit_dt = datetime.fromisoformat(iso)
            stat = entry_lines[i + 1].strip() if i + 1 < len(entry_lines) and entry_lines[i + 1].strip() else ""
            t = (commit_dt - start_dt).total_seconds()
            signals.append({"t": round(t, 2), "source": "git",
                             "data": f"commit {h[:7]} in {Path(repo_path).name}: {subject}" + (f" ({stat})" if stat else "")})
        i += 1
    return signals


def _extract_log_entry_text(d: dict):
    t = d.get("type")
    if t == "assistant":
        parts = []
        for c in d.get("message", {}).get("content", []):
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                inp = c.get("input", {})
                summary = inp.get("command") or inp.get("file_path") or inp.get("query") or inp.get("skill") or ""
                parts.append(f"ran {c.get('name')}: {str(summary)[:150]}")
            elif c.get("type") == "text":
                txt = c.get("text", "").strip()
                if txt:
                    parts.append(f"said: {txt[:220]}")
        return " | ".join(parts) if parts else None
    if t == "user":
        content = d.get("message", {}).get("content")
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    txt = c.get("content")
                    if isinstance(txt, list):
                        txt = " ".join(str(x.get("text", ""))[:150] for x in txt if isinstance(x, dict))
                    prefix = "ERROR result" if c.get("is_error") else "result"
                    return f"{prefix}: {str(txt)[:150]}"
    return None


def claude_code_signals(repo_paths: list, start_dt: datetime, end_dt: datetime) -> list:
    """Structured, precisely-timestamped tool-call/result activity straight
    from Claude Code's own session logs (~/.claude/projects/<slug>/*.jsonl) --
    verified far more reliable than OCR-reading a terminal screenshot for
    'what command ran, what it returned, did it fail.'"""
    signals = []
    claude_root = Path.home() / ".claude" / "projects"
    for repo_path in repo_paths:
        slug = str(Path(repo_path).resolve()).replace("/", "-")
        for jsonl_path in glob.glob(str(claude_root / slug / "*.jsonl")):
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = d.get("timestamp")
                    if not ts:
                        continue
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if not (start_dt <= dt <= end_dt):
                        continue
                    text = _extract_log_entry_text(d)
                    if text:
                        signals.append({"t": round((dt - start_dt).total_seconds(), 2),
                                         "source": "terminal", "data": text})
    return signals


def merge_timeline(*streams) -> list:
    merged = [entry for stream in streams for entry in stream]
    merged.sort(key=lambda e: e["t"])
    return merged
