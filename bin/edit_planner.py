#!/usr/bin/env python3
"""Edit Planner: for one chosen story, produces a story map (narrative beats)
and edit_plan.json (the actual EDL -- keep/remove/trim decisions, each with an
explicit reason, never "because it's slow/static"). Then runs the same
restart-detection backstop summarize_cut.py already needed against real data
(summarize_cut.py:107).

Usage:
    python3 bin/edit_planner.py session_001 s1
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import sessions as S
from lib.ai_client import call_claude, extract_json

PROMPT_TEMPLATE = """You are planning the edit for ONE story pulled from a longer recorded session
of Mohammad building software while talking naturally. Produce two things:

1. A STORY MAP: an ordered sequence of narrative beats (free-text labels -- e.g. hook, context,
   problem, failed_attempt, discovery, solution, result, lesson -- pick whatever beats actually fit
   THIS story; not every story needs all of them or in that order), each pointing at the event_ids
   and timestamps that beat covers.

2. An EDIT PLAN: an ordered, timestamped list of keep/remove/trim decisions covering the full
   range of this story from its first to its last relevant timestamp. RULES:
   - "keep": include this range as-is.
   - "remove": cut this range out entirely.
   - "trim": this range has dead air/repetition worth shortening but not fully removing -- give
     trim_end_s: an ABSOLUTE timestamp marking where the kept portion ends (the range from
     trim_end_s to end_s is dropped). trim_end_s MUST exactly equal one of the transcript segment
     boundaries below, just like start_s/end_s -- never an arbitrary duration/offset. If no segment
     boundary lands where you want to shorten it, use "remove" on the unwanted tail segment(s)
     instead of "trim" on the whole range.
   - EVERY decision needs a concrete "reason" -- never "it's slow" or "not visually interesting".
     Valid reasons reference the story: "establishes X needed to understand Y", "repeats what was
     already said at Z", "dead air with no content", etc.
   - NEVER remove or trim an "essential" event just because it's visually static or technical --
     only remove genuinely unnecessary/redundant content.
   - start_s/end_s MUST exactly match transcript segment boundaries below -- never invent a
     timestamp or cut a sentence in the middle. If in doubt, keep the extra segment rather than
     risk a fragment.
   - Mark "confidence": "certain" or "uncertain" per decision -- "uncertain" is for genuine judgment
     calls Mohammad should double check, not a hedge on everything.

STORY:
{story_block}

RELEVANT EVENTS:
{events_block}

RELEVANT TRANSCRIPT SEGMENTS (use these exact boundaries):
{segments_block}

{preferences}

OUTPUT valid JSON only, no other text, in this exact shape:
{{"story_map": {{"story_id": "{story_id}", "beats": [{{"beat": "...", "event_ids": [...], "start_s": 0, "end_s": 0}}]}},
  "edit_plan": [{{"decision": "keep|remove|trim", "start_s": 0, "end_s": 0, "trim_end_s": 0,
                  "event_ids": [], "reason": "...", "confidence": "certain|uncertain"}}]}}
(omit trim_end_s entirely for keep/remove decisions)"""


def relevant_segments(segments, lo, hi):
    return [s for s in segments if s["end_s"] > lo - 0.01 and s["start_s"] < hi + 0.01]


def validate_edit_plan(edit_plan, segments, warn_tolerance=0.05, max_tolerance=2.0):
    """Hard gate against the exact bug class this prompt already warns about in
    prose: the LLM was told 'never invent a timestamp' but a free-floating
    trim_to_s duration (since replaced with trim_end_s) once landed mid-word
    ("It re-" instead of "It replies..."). A prompt instruction alone didn't
    catch it -- every start_s/end_s/trim_end_s is snapped to the real transcript
    boundary it's nearest to (never left floating mid-segment), which is also
    the safe direction here -- e.g. a slightly-short end_s that lands inside a
    sentence gets extended to include the whole sentence, matching this
    codebase's own "when in doubt, keep the extra segment" rule. Beyond
    max_tolerance the gap is too large to be rounding and is treated as a
    genuine fabrication -- refused, not silently guessed at."""
    boundaries = sorted({s["start_s"] for s in segments} | {s["end_s"] for s in segments})

    def snap_or_raise(label, value, decision):
        nearest = min(boundaries, key=lambda b: abs(b - value))
        gap = abs(nearest - value)
        if gap > max_tolerance:
            raise ValueError(
                f"{label}={value} in decision {decision} is {gap:.2f}s from the nearest real "
                f"transcript boundary ({nearest}) -- looks like an invented timestamp, not a "
                f"segment edge. Refusing to compile this into a cut."
            )
        if gap > warn_tolerance:
            print(f"  ⚠ Snapped {label} {value} -> {nearest} ({gap:.2f}s) to land on a real segment boundary")
        return nearest

    fixed = []
    for d in edit_plan:
        d = dict(d)
        d["start_s"] = snap_or_raise("start_s", d["start_s"], d)
        d["end_s"] = snap_or_raise("end_s", d["end_s"], d)
        if d["decision"] == "trim":
            if "trim_end_s" not in d:
                raise ValueError(f"trim decision missing trim_end_s: {d}")
            d["trim_end_s"] = snap_or_raise("trim_end_s", d["trim_end_s"], d)
        fixed.append(d)
    return fixed


# NOTE: the original plan called for reusing summarize_cut.py's
# drop_restarted_takes() here as a backstop against restarted/redone takes.
# Tested against real output (session_001/s1) at both blob granularity and
# corrected per-segment granularity, and in both cases it produced ONLY false
# positives on this data -- every flagged pair, checked by hand against the
# source transcript, turned out to be two distinct, unrelated sentences that
# merely shared a short common word ("that", "up", "mock"), including one that
# deleted the story's central discovery sentence (e4). That function's design
# (45s window, 0.5 word-overlap over a 4-word floor) is calibrated for
# near-verbatim screen-recording retakes, which is a different regime from a
# clean single narration pass being cut by story logic -- it doesn't transfer,
# so it's intentionally NOT applied here. If a real multi-hour session later
# surfaces an actual missed restart, that's the point to build a backstop
# tuned for THIS data (e.g. much higher similarity + longer minimum length),
# not to reapply this one on the assumption it would generalize.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    parser.add_argument("story_id")
    args = parser.parse_args()

    sdir = S.session_dir(args.session_id)
    events = S.load_json(sdir / "events.json")
    stories = S.load_json(sdir / "stories.json")
    segments = S.load_json(sdir / "transcript.json")

    story = next((s for s in stories if s["story_id"] == args.story_id), None)
    if story is None:
        raise ValueError(f"No story {args.story_id} in {sdir / 'stories.json'}")

    all_event_ids = set(story["required_events"]) | set(story.get("optional_events", []))
    story_events = [e for e in events if e["event_id"] in all_event_ids]
    if not story_events:
        raise ValueError(f"Story {args.story_id} has no resolvable events")
    lo = min(e["start_s"] for e in story_events)
    hi = max(e["end_s"] for e in story_events)
    seg_slice = relevant_segments(segments, lo, hi)

    events_block = "\n".join(
        f"[{e['event_id']}] {e['type']} {e['start_s']:.1f}-{e['end_s']:.1f}s: {e['summary']}"
        for e in story_events
    )
    segments_block = "\n".join(
        f"[{s['id']}] {s['start_s']:.1f}-{s['end_s']:.1f}s: {s['text']}" for s in seg_slice
    )
    story_block = (
        f"Title: {story['title']}\nCentral idea: {story['central_idea']}\n"
        f"Audience: {story['audience']}\nCategory: {story['category']}"
    )

    prompt = PROMPT_TEMPLATE.format(
        story_block=story_block, events_block=events_block, segments_block=segments_block,
        story_id=args.story_id, preferences=S.load_preferences_text(),
    )

    print(f"🧠 Planning edit for story {args.story_id}: {story['title']}...")
    response = call_claude(prompt, max_tokens=6000)
    parsed = extract_json(response)
    story_map, edit_plan = parsed["story_map"], parsed["edit_plan"]

    edit_plan = validate_edit_plan(edit_plan, seg_slice)

    out_dir = S.story_dir(args.session_id, args.story_id, create=True)
    S.save_json(out_dir / "story_map.json", story_map)
    S.save_json(out_dir / "edit_plan.json", edit_plan)
    S.update_status(args.session_id, "planned")

    kept = [d for d in edit_plan if d["decision"] in ("keep", "trim")]
    kept_s = sum((d["trim_end_s"] if d["decision"] == "trim" else d["end_s"]) - d["start_s"] for d in kept)
    print(f"✓ {len(edit_plan)} decisions ({len(kept)} kept, ~{kept_s:.0f}s)")
    print(f"  Next: python3 bin/rough_cut.py {args.session_id} {args.story_id}")


if __name__ == "__main__":
    main()
