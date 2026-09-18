#!/usr/bin/env python3
"""Edit Planner: for one chosen story, produces a story map (narrative beats)
and edit_plan.json (the actual EDL -- keep/remove/trim decisions, each with an
explicit reason, never "because it's slow/static"), reasoning over the FULL
multi-source timeline (screen/OCR, audio if present, git, terminal activity).

Cut-boundary candidates are kept separate from reasoning context: OCR/git/
terminal timeline entries are single POINTS in time (a sample, a commit, a
logged command) with no natural "end," so they inform WHAT happened but are
not valid cut edges. Only scene-change timestamps (real visual boundaries)
and audio-segment edges (real speech boundaries) are legitimate places to cut
-- that's the set every decision must snap to.

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
of Mohammad building software -- possibly screen-only with no narration, possibly with real audio,
possibly with both. Produce two things:

1. A STORY MAP: an ordered sequence of narrative beats (free-text labels -- e.g. hook, context,
   problem, failed_attempt, discovery, solution, result, lesson -- pick whatever beats actually fit
   THIS story; not every story needs all of them or in that order), each pointing at the event_ids
   and timestamps that beat covers.

2. An EDIT PLAN: an ordered, timestamped list of keep/remove/trim decisions covering the full
   range of this story from its first to its last relevant timestamp. RULES:
   - "keep": include this range as-is.
   - "remove": cut this range out entirely.
   - "trim": this range has dead air/repetition worth shortening but not fully removing -- give
     trim_end_s: an ABSOLUTE timestamp marking where the kept portion ends. trim_end_s MUST exactly
     equal one of the CUT-BOUNDARY CANDIDATES below, just like start_s/end_s -- never an arbitrary
     duration/offset. If no boundary lands where you want to shorten it, use "remove" on the
     unwanted tail instead of "trim" on the whole range.
   - EVERY decision needs a concrete "reason" tied to the story -- never "it's slow" or "not
     visually interesting". A silent stretch where the screen shows a real result appearing, or a
     command finishing, is NOT dead air just because no one is talking -- check the timeline for
     what's actually happening on screen before deciding it's cuttable.
   - NEVER remove or trim an "essential" event just because it's visually static or technical --
     only remove genuinely unnecessary/redundant content.
   - start_s/end_s/trim_end_s MUST exactly match one of the CUT-BOUNDARY CANDIDATES listed below --
     never invent a timestamp. If in doubt, keep the extra range rather than risk a bad cut.
   - Mark "confidence": "certain" or "uncertain" per decision.
   - Optionally set "speed" (e.g. 2.0) on a "keep" decision to speed through genuinely repetitive
     or low-value activity that's still worth SHOWING but not at full length (e.g. watching a slow
     build run) -- omit it (defaults to 1.0) otherwise.
   - Optionally set "preserve_realtime": true on a decision that captures a real-time failure or
     success moment that must play at normal speed, uncut, even if it looks static -- this
     overrides any speed-up and signals "do not touch the pacing of this range."
   - Optionally set "zoom_target" (a short phrase, e.g. "terminal output", "browser result") when
     the viewer's attention should be directed at a specific area, and "highlight_note" (a short
     phrase describing what should visually stand out, e.g. "the error message"). These are
     editorial hints for a later visual pass -- describe intent, don't worry about exact pixels.
   - IMPORTANT: if the timeline for this story ends mid-investigation or without a confirmed
     resolution, the edit plan's last decision(s) and the story map's final beat must reflect that
     honestly -- do not invent or imply a successful resolution that isn't actually evidenced in
     the timeline.

STORY:
{story_block}

RELEVANT EVENTS:
{events_block}

RELEVANT TIMELINE (all sources, for context -- NOT all of these are valid cut points):
{timeline_block}

CUT-BOUNDARY CANDIDATES (start_s/end_s/trim_end_s must be one of these exact values):
{boundaries_block}

{preferences}

OUTPUT valid JSON only, no other text, in this exact shape:
{{"story_map": {{"story_id": "{story_id}", "beats": [{{"beat": "...", "event_ids": [...], "start_s": 0, "end_s": 0}}]}},
  "edit_plan": [{{"decision": "keep|remove|trim", "start_s": 0, "end_s": 0, "trim_end_s": 0,
                  "event_ids": [], "reason": "...", "confidence": "certain|uncertain",
                  "speed": 1.0, "preserve_realtime": false, "zoom_target": "", "highlight_note": ""}}]}}
(omit trim_end_s for keep/remove; omit speed/preserve_realtime/zoom_target/highlight_note when not applicable)"""


def load_boundaries(sdir, lo: float, hi: float, pad: float = 0.5) -> list:
    """Legit cut edges only: scene-change (OCR sample) timestamps and, if
    audio exists, transcript segment start/end -- NOT raw git/terminal points,
    which mark real-world events but have no natural video-cut edge."""
    timeline = S.load_json(sdir / "timeline.json")
    boundaries = {round(e["t"], 2) for e in timeline if e["source"] == "ocr"}
    transcript_path = sdir / "transcript.json"
    if transcript_path.exists():
        segs = S.load_json(transcript_path)
        boundaries |= {s["start_s"] for s in segs} | {s["end_s"] for s in segs}
    return sorted(b for b in boundaries if lo - pad <= b <= hi + pad)


def relevant_timeline(sdir, lo: float, hi: float, pad: float = 0.5) -> list:
    timeline = S.load_json(sdir / "timeline.json")
    return [e for e in timeline if lo - pad <= e["t"] <= hi + pad]


def validate_edit_plan(edit_plan: list, boundaries: list, tolerance=0.05, max_tolerance=2.0) -> list:
    """Hard gate, not just a prompt instruction (a prompt-only version of this
    rule already failed once in this project's own history on this exact
    pipeline -- see git history / session learnings). Every timestamp is
    snapped to the nearest real boundary; beyond max_tolerance it's refused as
    a likely fabrication rather than silently guessed at."""
    if not boundaries:
        raise ValueError("No cut-boundary candidates available for this story's time range -- "
                          "cannot validate an edit plan against nothing.")

    def snap_or_raise(label, value, decision):
        nearest = min(boundaries, key=lambda b: abs(b - value))
        gap = abs(nearest - value)
        if gap > max_tolerance:
            raise ValueError(f"{label}={value} in decision {decision} is {gap:.2f}s from the nearest "
                              f"real boundary ({nearest}) -- looks fabricated, refusing to compile.")
        if gap > tolerance:
            print(f"  ⚠ Snapped {label} {value} -> {nearest} ({gap:.2f}s)")
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
        d.setdefault("speed", 1.0)
        d.setdefault("preserve_realtime", False)
        fixed.append(d)
    return fixed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    parser.add_argument("story_id")
    args = parser.parse_args()

    sdir = S.session_dir(args.session_id)
    events = S.load_json(sdir / "events.json")
    stories = S.load_json(sdir / "stories.json")

    story = next((s for s in stories if s["story_id"] == args.story_id), None)
    if story is None:
        raise ValueError(f"No story {args.story_id} in {sdir / 'stories.json'}")

    all_event_ids = set(story["required_events"]) | set(story.get("optional_events", []))
    story_events = [e for e in events if e["event_id"] in all_event_ids]
    if not story_events:
        raise ValueError(f"Story {args.story_id} has no resolvable events")
    lo = min(e["start_s"] for e in story_events)
    hi = max(e["end_s"] for e in story_events)

    timeline_slice = relevant_timeline(sdir, lo, hi)
    boundaries = load_boundaries(sdir, lo, hi)

    events_block = "\n".join(
        f"[{e['event_id']}] {e['type']} {e['start_s']:.1f}-{e['end_s']:.1f}s [{','.join(e.get('sources', []))}]: {e['summary']}"
        for e in story_events
    )
    timeline_block = "\n".join(f"[{e['source']}] {e['t']:.1f}s: {e['data']}" for e in timeline_slice)
    boundaries_block = ", ".join(f"{b:.2f}" for b in boundaries)
    story_block = (
        f"Title: {story['title']}\nCentral idea: {story['central_idea']}\n"
        f"Audience: {story['audience']}\nCategory: {story['category']}"
    )

    prompt = PROMPT_TEMPLATE.format(
        story_block=story_block, events_block=events_block, timeline_block=timeline_block,
        boundaries_block=boundaries_block, story_id=args.story_id, preferences=S.load_preferences_text(),
    )

    print(f"🧠 Planning edit for story {args.story_id}: {story['title']}...")
    response = call_claude(prompt, max_tokens=6000)
    parsed = extract_json(response)
    story_map, edit_plan = parsed["story_map"], parsed["edit_plan"]

    edit_plan = validate_edit_plan(edit_plan, boundaries)

    out_dir = S.story_dir(args.session_id, args.story_id, create=True)
    S.save_json(out_dir / "story_map.json", story_map)
    S.save_json(out_dir / "edit_plan.json", edit_plan)
    S.update_status(args.session_id, "planned")

    kept = [d for d in edit_plan if d["decision"] in ("keep", "trim")]
    kept_s = sum((d["trim_end_s"] if d["decision"] == "trim" else d["end_s"]) - d["start_s"] for d in kept)
    sped = [d for d in kept if d.get("speed", 1.0) != 1.0]
    print(f"✓ {len(edit_plan)} decisions ({len(kept)} kept, ~{kept_s:.0f}s raw, {len(sped)} sped up)")
    print(f"  Next: python3 bin/rough_cut.py {args.session_id} {args.story_id}")


if __name__ == "__main__":
    main()
