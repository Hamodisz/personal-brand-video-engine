#!/usr/bin/env python3
"""Session Review: a dashboard + correction CLI over sessions/, modeled on
queue_status.py's pattern for content_queue/. Mohammad should be able to
review a story without re-watching the source recording.

Usage:
    python3 bin/session_review.py list
    python3 bin/session_review.py show session_001 [s1]
    python3 bin/session_review.py approve session_001 s1
    python3 bin/session_review.py correct session_001 s1 --restore 42.0-55.0 --reason "..."
    python3 bin/session_review.py correct session_001 s1 --cut 10.0-15.0 --reason "..."
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import sessions as S

ROOT = Path(__file__).parent.parent


def cmd_list(args):
    ids = S.all_session_ids()
    if not ids:
        print('No sessions yet. Run: python3 bin/session_ingest.py --video <path> --note "..."')
        return
    for sid in ids:
        meta = S.load_meta(sid)
        print(f"{sid}  [{meta['status']:<14}]  {meta.get('topic_note', '') or meta.get('slug', '')}"
              f"  ({meta.get('duration_s', 0):.0f}s)")


def cmd_show(args):
    sdir = S.session_dir(args.session_id)
    meta = S.load_meta(args.session_id)
    print(f"=== {args.session_id} ({meta['status']}) ===")
    print(f"Note: {meta.get('topic_note', '(none)')}")
    print(f"Duration: {meta.get('duration_s', 0):.0f}s\n")

    stories_path = sdir / "stories.json"
    if not stories_path.exists():
        print("No stories mined yet.")
        return
    stories = S.load_json(stories_path)
    print(f"STORIES FOUND: {len(stories)}")
    for s in stories:
        print(f"  [{s['story_id']}] {s['title']}  ({s['category']})")

    if args.story_id:
        story = next((s for s in stories if s["story_id"] == args.story_id), None)
        if story is None:
            print(f"\nNo story {args.story_id}")
            return
        other = [s["title"] for s in stories if s["story_id"] != args.story_id]
        print(f"\n=== STORY {args.story_id}: {story['title']} ===")
        print(f"Central idea: {story['central_idea']}")
        if other:
            print(f"Other stories in this session not chosen: {', '.join(other)}")

        plan_path = S.story_dir(args.session_id, args.story_id) / "edit_plan.json"
        if not plan_path.exists():
            print("\nNo edit plan yet -- run edit_planner.py")
            return
        edit_plan = S.load_json(plan_path)
        counts = {"keep": 0, "remove": 0, "trim": 0}
        for d in edit_plan:
            counts[d["decision"]] += 1
        print(f"\nDECISIONS: keep={counts['keep']} remove={counts['remove']} trim={counts['trim']}")
        print("\nALL REASONS:")
        for d in edit_plan:
            flag = " ⚠ UNCERTAIN" if d.get("confidence") == "uncertain" else ""
            print(f"  [{d['decision']:>6}] {d['start_s']:.1f}-{d['end_s']:.1f}s: {d['reason']}{flag}")


def cmd_approve(args):
    subprocess.run([sys.executable, str(ROOT / "bin" / "rough_cut.py"),
                    args.session_id, args.story_id, "--preview"], check=True)
    S.update_status(args.session_id, "reviewed")


def _parse_range(s: str):
    lo, hi = s.split("-")
    return float(lo), float(hi)


def cmd_correct(args):
    plan_path = S.story_dir(args.session_id, args.story_id) / "edit_plan.json"
    edit_plan = S.load_json(plan_path)

    if args.restore:
        lo, hi = _parse_range(args.restore)
        edit_plan.append({
            "decision": "keep", "start_s": lo, "end_s": hi, "event_ids": [],
            "reason": args.reason or "manually restored by Mohammad", "confidence": "certain",
        })
        edit_plan.sort(key=lambda d: d["start_s"])
        S.append_preference(
            f"preserve segments like {args.reason or 'this one'} even if a previous pass cut them",
            source=f"{args.session_id}/{args.story_id} restore {args.restore}",
        )
    elif args.cut:
        lo, hi = _parse_range(args.cut)
        for d in edit_plan:
            if d["decision"] in ("keep", "trim") and d["start_s"] >= lo - 0.01 and d["end_s"] <= hi + 0.01:
                d["decision"] = "remove"
                d["reason"] = args.reason or "manually cut by Mohammad"
        S.append_preference(
            f"cut segments like {args.reason or 'this one'} even if a previous pass kept them",
            source=f"{args.session_id}/{args.story_id} cut {args.cut}",
        )
    else:
        print("Specify --restore <start>-<end> or --cut <start>-<end>")
        return

    S.save_json(plan_path, edit_plan)
    print(f"✓ edit_plan.json updated -- re-run: python3 bin/rough_cut.py {args.session_id} {args.story_id} --preview")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")

    p_show = sub.add_parser("show")
    p_show.add_argument("session_id")
    p_show.add_argument("story_id", nargs="?", default=None)

    p_approve = sub.add_parser("approve")
    p_approve.add_argument("session_id")
    p_approve.add_argument("story_id")

    p_correct = sub.add_parser("correct")
    p_correct.add_argument("session_id")
    p_correct.add_argument("story_id")
    p_correct.add_argument("--restore", default=None, help="start-end seconds, e.g. 42.0-55.0")
    p_correct.add_argument("--cut", default=None, help="start-end seconds, e.g. 10.0-15.0")
    p_correct.add_argument("--reason", default=None)

    args = parser.parse_args()
    {"list": cmd_list, "show": cmd_show, "approve": cmd_approve, "correct": cmd_correct}[args.cmd](args)


if __name__ == "__main__":
    main()
