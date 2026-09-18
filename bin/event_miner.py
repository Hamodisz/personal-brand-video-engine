#!/usr/bin/env python3
"""Event Miner: breaks a session's transcript into typed, timestamped events
with explicit dependencies -- the causal chain the spec insists on, not an
interestingness score. Reuses summarize_cut.py's transcript-block format and
ID-validation pattern (summarize_cut.py:61,100).

Usage:
    python3 bin/event_miner.py session_001
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import sessions as S
from lib.ai_client import call_claude, extract_json

EVENT_TYPES = [
    "problem", "goal", "setup", "attempt", "failure", "mistake", "discovery",
    "insight", "decision", "conflict", "debugging", "solution", "transformation",
    "result", "lesson", "reaction", "surprising_moment", "demonstration",
]

PROMPT_TEMPLATE = """This is a timestamped transcript of Mohammad recording himself building
software (talking naturally while he works). Break it into a sequence of discrete,
timestamped EVENTS describing what actually happened -- not a summary, an event log.

{context}

EVENT TYPES (pick the closest one per event): {event_types}

For each event give:
- event_id: "e1", "e2", ... in chronological order
- type: one of the event types above
- start_s / end_s: must come from the transcript segment boundaries below -- never invent a timestamp
- summary: one line, what happened
- explanation: why this matters for understanding what comes AFTER it (not why it's interesting)
- importance: "essential" | "supporting" | "cuttable"
    - essential: a later event genuinely depends on this one, OR it's the problem/solution/result anchor
    - supporting: adds clarity but isn't required to follow the story
    - cuttable: redundant, dead air, or off-topic -- genuinely unnecessary, not just slow or quiet
  Do NOT use importance as an "is this exciting" score. A technically boring segment (e.g. explaining
  a root cause) can still be essential. Ask: does understanding a LATER event require this one?
- depends_on: a list of EARLIER event_ids this one depends on to make sense (e.g. a "solution" event
  usually depends_on the "problem"/"discovery" events that motivated it). Use [] if none. Only
  reference event_ids you yourself are assigning in this same list.

{preferences}

TRANSCRIPT:
{transcript_block}

OUTPUT valid JSON only, no other text: a JSON array of event objects as described above."""


def build_transcript_block(segments: list) -> str:
    return "\n".join(f"[{s['id']}] {s['start_s']:.1f}-{s['end_s']:.1f}s: {s['text']}" for s in segments)


def validate_events(events: list) -> list:
    ids = {e["event_id"] for e in events}
    for e in events:
        bad = [d for d in e.get("depends_on", []) if d not in ids]
        if bad:
            raise ValueError(f"Event {e['event_id']} depends_on unknown ids {bad} -- model hallucinated a reference.")
        if e["type"] not in EVENT_TYPES:
            raise ValueError(f"Event {e['event_id']} has unknown type {e['type']!r}.")
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    args = parser.parse_args()

    sdir = S.session_dir(args.session_id)
    segments = S.load_json(sdir / "transcript.json")
    meta = S.load_meta(args.session_id)

    context = f"Context Mohammad gave for this session: {meta['topic_note']}" if meta.get("topic_note") else ""
    preferences = S.load_preferences_text()
    transcript_block = build_transcript_block(segments)

    prompt = PROMPT_TEMPLATE.format(
        context=context, event_types=", ".join(EVENT_TYPES),
        preferences=preferences, transcript_block=transcript_block,
    )

    print(f"🧠 Mining events from {len(segments)} transcript segments...")
    response = call_claude(prompt, max_tokens=8000)
    events = extract_json(response)
    events = validate_events(events)

    S.save_json(sdir / "events.json", events)
    S.update_status(args.session_id, "events_mined")

    counts = {}
    for e in events:
        counts[e["importance"]] = counts.get(e["importance"], 0) + 1
    print(f"✓ {len(events)} events: {counts}")
    print(f"  Next: python3 bin/story_miner.py {args.session_id}")


if __name__ == "__main__":
    main()
