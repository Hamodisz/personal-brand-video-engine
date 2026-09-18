"""Resolves a working ffmpeg + imports summarize_cut.py's reusable functions.

~/bin/ffmpeg (the path every existing script in this repo hardcodes) is an
x86_64 binary, and Rosetta isn't installed/working on this machine (confirmed:
`arch -x86_64 /usr/bin/true` fails with "Bad CPU type in executable" even with
sandboxing off) — so it currently cannot run at all. This does NOT touch
~/bin/ffmpeg or any existing script; it just resolves a working arm64-native
ffmpeg (bundled with the already-installed imageio-ffmpeg pip package) and
monkey-patches summarize_cut.py's module-level FFMPEG constant at runtime so
its already-hardened functions (normalize_source/cut_and_crop/verify_output_
duration/drop_restarted_takes/transcribe) work unmodified.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
BIN = ROOT / "bin"

_resolved_ffmpeg = None
_path_shim_dir = None


def resolve_ffmpeg() -> str:
    global _resolved_ffmpeg
    if _resolved_ffmpeg:
        return _resolved_ffmpeg
    candidate = str(Path.home() / "bin" / "ffmpeg")
    try:
        subprocess.run([candidate, "-version"], capture_output=True, timeout=10)
        _resolved_ffmpeg = candidate
        return _resolved_ffmpeg
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        import imageio_ffmpeg
        _resolved_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        return _resolved_ffmpeg
    except ImportError:
        raise RuntimeError(
            "No working ffmpeg found: ~/bin/ffmpeg won't run (likely x86_64 on an "
            "arm64 machine with no Rosetta) and imageio-ffmpeg isn't installed either "
            "(pip3 install imageio-ffmpeg)."
        )


def ensure_ffmpeg_on_path() -> None:
    """whisper's own audio loader (whisper/audio.py:load_audio) shells out to the
    literal command "ffmpeg" via PATH -- it has no idea about summarize_cut's
    FFMPEG constant. Prepend a symlink to a working binary onto THIS PROCESS's
    PATH only; no system files or shell rc files are touched."""
    global _path_shim_dir
    if _path_shim_dir:
        return
    working = resolve_ffmpeg()
    _path_shim_dir = tempfile.mkdtemp(prefix="ffmpeg_shim_")
    link = Path(_path_shim_dir) / "ffmpeg"
    if not link.exists():
        link.symlink_to(working)
    os.environ["PATH"] = f"{_path_shim_dir}:{os.environ.get('PATH', '')}"


def load_summarize_cut():
    """Import bin/summarize_cut.py as a module and point its FFMPEG constant
    at a working binary, without editing the file on disk."""
    if str(BIN) not in sys.path:
        sys.path.insert(0, str(BIN))
    import summarize_cut
    summarize_cut.FFMPEG = resolve_ffmpeg()
    ensure_ffmpeg_on_path()
    return summarize_cut
