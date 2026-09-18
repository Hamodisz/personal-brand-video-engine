#!/usr/bin/env python3
"""Story Miner: given events.json, finds every genuinely distinct story a
session could produce -- one session, many stories (spec section 4/6).

Usage:
    python3 bin/story_miner.py session_001
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import sessions as S
from lib.ai_client import call_claude, extract_json

CATEGORIES = [
    "build_in_public", "educational", "story", "mistake_failure", "demonstration",
    "opinion", "case_study", "tutorial", "discovery", "before_after", "technical_explanation",
]

PROMPT_TEMPLATE = """These are the typed events mined from one of Mohammad's recorded work
sessions (building software, talking naturally while he works). Find every genuinely distinct
STORY this single session could produce as short-form content -- a session is not automatically
one video; look for multiple independent narrative threads if they exist (e.g. "Claude broke my
recommendation system", "how I added a chatbot", "a mistake I made delegating to Claude Code" can
all live in the same session). If the session really only supports one coherent story, return one.

{context}

{preferences}

For each story give:
- story_id: "s1", "s2", ...
- title: a working title
- category: one of {categories}
- central_idea: the one sentence this story proves or shows
- audience: who this is for
- required_events: event_ids that MUST be included for the story to make sense
- optional_events: event_ids that add value but could be cut for a shorter version
- unnecessary_events: event_ids from this session that are irrelevant to THIS particular story
  (an event can appear in zero, one, or multiple stories' lists)
- hook_candidates: 2-3 possible opening hooks

Only reference event_ids that actually appear in the EVENTS list below -- never invent one.

EVENTS:
{events_block}

OUTPUT valid JSON only, no other text: a JSON array of story objects as described above."""


def build_events_block(events: list) -> str:
    lines = []
    for e in events:
        deps = f" (depends_on: {e['depends_on']})" if e.get("depends_on") else ""
        lines.append(f"[{e['event_id']}] {e['type']} {e['start_s']:.1f}-{e['end_s']:.1f}s "
                      f"[{e['importance']}]{deps}: {e['summary']} -- {e['explanation']}")
    return "\n".join(lines)


def validate_stories(stories: list, event_ids: set) -> list:
    for s in stories:
        for field in ("required_events", "optional_events", "unnecessary_events"):
            bad = [eid for eid in s.get(field, []) if eid not in event_ids]
            if bad:
                raise ValueError(f"Story {s['story_id']}.{field} references unknown event_ids {bad}.")
    return stories


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    args = parser.parse_args()

    sdir = S.session_dir(args.session_id)
    events = S.load_json(sdir / "events.json")
    meta = S.load_meta(args.session_id)

    context = f"Context Mohammad gave for this session: {meta['topic_note']}" if meta.get("topic_note") else ""
    events_block = build_events_block(events)

    prompt = PROMPT_TEMPLATE.format(
        context=context, preferences=S.load_preferences_text(), categories=", ".join(CATEGORIES),
        events_block=events_block,
    )

    print(f"🧠 Mining stories from {len(events)} events...")
    response = call_claude(prompt, max_tokens=6000)
    stories = extract_json(response)
    stories = validate_stories(stories, {e["event_id"] for e in events})

    S.save_json(sdir / "stories.json", stories)
    S.update_status(args.session_id, "stories_mined")

    print(f"✓ {len(stories)} candidate stories found:")
    for s in stories:
        print(f"  [{s['story_id']}] {s['title']} ({s['category']})")
    print(f"  Next: python3 bin/edit_planner.py {args.session_id} <story_id>")


if __name__ == "__main__":
    main()
