#!/usr/bin/env python3
"""Event Miner: breaks a session's MERGED MULTI-SOURCE timeline (screen/OCR,
audio if present, git commits, Claude Code terminal activity) into typed,
timestamped events with explicit dependencies -- the causal chain the spec
insists on, not an interestingness score, and not dependent on any single
signal being present.

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

SOURCE_LABELS = {
    "audio": "SPOKEN (what was said)",
    "ocr": "ON-SCREEN TEXT (what was visible: code, terminal output, errors, UI)",
    "git": "GIT (what actually changed in the project)",
    "terminal": "CLAUDE CODE / TOOL ACTIVITY (structured log: commands run, results, failures)",
}

PROMPT_TEMPLATE = """This is a MERGED, multi-source timeline of Mohammad recording himself
building software. Every line is tagged with WHICH signal it came from -- they are NOT all
speech. Some sessions have real narration; some are screen-only with no audio at all. Treat
every source as first-class evidence: a GIT line telling you a file changed is just as real as
an OCR line showing an error on screen or a SPOKEN line explaining intent. Cross-check them
against each other -- e.g. a SPOKEN "let's try this" followed by a TERMINAL command failing
followed by an OCR error message followed by a GIT commit fixing it is ONE causal chain, not
four disconnected clips.

Break this timeline into a sequence of discrete, timestamped EVENTS describing what actually
happened -- not a summary, an event log.

{context}

EVENT TYPES (pick the closest one per event): {event_types}

For each event give:
- event_id: "e1", "e2", ... in chronological order
- type: one of the event types above
- start_s / end_s: must come from the timeline entries below -- never invent a timestamp
- summary: one line, what happened
- explanation: why this matters for understanding what comes AFTER it (not why it's interesting)
- importance: "essential" | "supporting" | "cuttable"
    - essential: a later event genuinely depends on this one, OR it's the problem/solution/result anchor
    - supporting: adds clarity but isn't required to follow the story
    - cuttable: redundant, dead air, or off-topic -- genuinely unnecessary, not just slow or quiet
  Do NOT use importance as an "is this exciting" score. A technically boring segment (e.g. a
  git commit with no visible drama) can still be essential. Ask: does understanding a LATER
  event require this one?
- depends_on: a list of EARLIER event_ids this one depends on to make sense. Use [] if none.
  Only reference event_ids you yourself are assigning in this same list.
- sources: which signal type(s) from the timeline this event is grounded in, e.g. ["ocr"],
  ["audio","terminal"], ["git"]. Be honest -- if you inferred something from OCR text alone,
  say ["ocr"], don't claim ["audio"] unless a SPOKEN line actually supports it.
- IMPORTANT -- do not assume a resolution that isn't actually in the timeline. If the timeline
  ends mid-investigation or mid-failure with no confirming signal of success, the last event
  must reflect that honestly (e.g. type "debugging" or "surprising_moment", not "result" or
  "lesson") rather than assuming things worked out.

{preferences}

TIMELINE (source in brackets):
{timeline_block}

OUTPUT valid JSON only, no other text: a JSON array of event objects as described above."""


def build_timeline_block(timeline: list) -> str:
    return "\n".join(f"[{e['source']}] {e['t']:.1f}s: {e['data']}" for e in timeline)


def validate_events(events: list) -> list:
    ids = {e["event_id"] for e in events}
    for e in events:
        bad = [d for d in e.get("depends_on", []) if d not in ids]
        if bad:
            raise ValueError(f"Event {e['event_id']} depends_on unknown ids {bad} -- model hallucinated a reference.")
        if e["type"] not in EVENT_TYPES:
            raise ValueError(f"Event {e['event_id']} has unknown type {e['type']!r}.")
        if not e.get("sources"):
            raise ValueError(f"Event {e['event_id']} has no sources -- every event must cite what it's grounded in.")
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    args = parser.parse_args()

    sdir = S.session_dir(args.session_id)
    timeline = S.load_json(sdir / "timeline.json")
    if not timeline:
        raise ValueError(f"{sdir}/timeline.json is empty -- nothing to mine events from.")
    meta = S.load_meta(args.session_id)

    context = f"Context Mohammad gave for this session: {meta['topic_note']}" if meta.get("topic_note") else ""
    preferences = S.load_preferences_text()
    timeline_block = build_timeline_block(timeline)

    prompt = PROMPT_TEMPLATE.format(
        context=context, event_types=", ".join(EVENT_TYPES),
        preferences=preferences, timeline_block=timeline_block,
    )

    print(f"🧠 Mining events from {len(timeline)} timeline entries "
          f"({', '.join(sorted({e['source'] for e in timeline}))})...")
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
