"""Shared Anthropic API client for the session pipeline scripts.

Lifted from bin/summarize_cut.py's ask_claude()/_load_api_key() — that file is
left untouched; this is only for the new session_*/event_miner/story_miner/
edit_planner scripts so they don't each re-duplicate the same 20 lines.
"""
import json
import os
import urllib.request
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"


def _load_api_key() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        return api_key
    for f in (ROOT / ".env.local", ROOT / ".env"):
        if f.exists():
            for line in f.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"\'')
    raise RuntimeError("ANTHROPIC_API_KEY not set")


def call_claude(prompt: str, system: Optional[str] = None, max_tokens: int = 4096) -> str:
    api_key = _load_api_key()
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=json.dumps(payload).encode(),
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["content"][0]["text"]


def extract_json(text: str):
    """Pull the first top-level JSON object/array out of a model response,
    tolerating leading/trailing prose the model sometimes adds despite instructions."""
    start_obj, start_arr = text.find("{"), text.find("[")
    candidates = [c for c in (start_obj, start_arr) if c != -1]
    if not candidates:
        raise ValueError(f"No JSON found in response: {text[:200]}")
    start = min(candidates)
    end = max(text.rfind("}"), text.rfind("]")) + 1
    return json.loads(text[start:end])
