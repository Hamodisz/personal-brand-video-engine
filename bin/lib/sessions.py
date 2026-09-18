"""Shared session-directory helpers for the session pipeline scripts.

Mirrors the directory-per-item + flat-JSON convention already proven by
content_queue/*/loop.json + queue_status.py — no database.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SESSIONS_DIR = ROOT / "sessions"
PREFERENCES_PATH = SESSIONS_DIR / "preferences.json"

STATUSES = [
    "ingested", "transcribed", "events_mined", "stories_mined",
    "planned", "rough_cut", "reviewed",
]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:max_len] or "session"


def next_session_id() -> str:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    existing = [d.name for d in SESSIONS_DIR.iterdir() if d.is_dir() and d.name.startswith("session_")]
    nums = [int(m.group(1)) for n in existing if (m := re.match(r"session_(\d+)$", n))]
    return f"session_{(max(nums) + 1) if nums else 1:03d}"


def session_dir(session_id: str) -> Path:
    d = SESSIONS_DIR / session_id
    if not d.exists():
        raise FileNotFoundError(f"No such session: {session_id} (looked in {d})")
    return d


def new_session_dir(session_id: str) -> Path:
    d = SESSIONS_DIR / session_id
    d.mkdir(parents=True, exist_ok=False)
    return d


def story_dir(session_id: str, story_id: str, create: bool = False) -> Path:
    d = session_dir(session_id) / "stories" / story_id
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def all_session_ids() -> list:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(d.name for d in SESSIONS_DIR.iterdir() if d.is_dir() and d.name.startswith("session_"))


def load_meta(session_id: str) -> dict:
    return load_json(session_dir(session_id) / "meta.json")


def update_status(session_id: str, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"Unknown status {status!r}, expected one of {STATUSES}")
    meta_path = session_dir(session_id) / "meta.json"
    meta = load_json(meta_path)
    meta["status"] = status
    save_json(meta_path, meta)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_preferences_text() -> str:
    """Extra context injected into event/story/edit-plan prompts. Empty until
    session_review.py's `correct` command appends the first real entry — Phase 6
    stub, not the full preference-learning system from the spec."""
    if not PREFERENCES_PATH.exists():
        return ""
    prefs = load_json(PREFERENCES_PATH)
    if not prefs:
        return ""
    lines = "\n".join(f"- {p['rule']}" for p in prefs)
    return f"\n\nMohammad's accumulated editing preferences from past corrections — apply these:\n{lines}"


def append_preference(rule: str, source: str) -> None:
    prefs = load_json(PREFERENCES_PATH) if PREFERENCES_PATH.exists() else []
    prefs.append({"rule": rule, "source": source, "added_at": now_iso()})
    save_json(PREFERENCES_PATH, prefs)
