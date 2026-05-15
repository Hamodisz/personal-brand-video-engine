#!/usr/bin/env python3
"""
templates.py — CapCut-style template toolkit for personal brand videos

Commands:
  python3 bin/templates.py list                        # show all templates
  python3 bin/templates.py use <name>                  # copy template → shot_plan.json
  python3 bin/templates.py save <name> [--desc "..."]  # save current shot_plan as template
  python3 bin/templates.py info <name>                 # show full template shot plan
  python3 bin/templates.py delete <name>               # delete a saved template
  python3 bin/templates.py preview <name>              # render a test still (frame 60)
"""
import sys
import os
import json
import shutil
import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
SHOT_PLAN = PROJECT_ROOT / "public" / "shot_plan.json"
PUBLIC = PROJECT_ROOT / "public"


STYLE_ICONS = {
    "talking_head":    "🎙",
    "broll_fullscreen":"🎬",
    "pip":             "🪟",
    "text_cards":      "📝",
    "website_overlay": "🌐",
    "stat_callout":    "📊",
    "cta_closer":      "🔥",
}


def load_template(name):
    path = TEMPLATES_DIR / name
    if not path.exists():
        print(f"ERROR: Template '{name}' not found.")
        print("Run `python3 bin/templates.py list` to see available templates.")
        sys.exit(1)
    with open(path / "shot_plan.json") as f:
        plan = json.load(f)
    meta_path = path / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    return plan, meta


def shot_summary(shots):
    parts = []
    for s in shots:
        icon = STYLE_ICONS.get(s["style"], "▪")
        dur = s["end_s"] - s["start_s"]
        parts.append(f"{icon}{s['style']}({dur:.0f}s)")
    return " → ".join(parts)


def cmd_list(args):
    dirs = sorted(d for d in TEMPLATES_DIR.iterdir() if d.is_dir())
    if not dirs:
        print("No templates found.")
        return

    print()
    print(f"  {'NAME':<22} {'DURATION':<10} {'STRUCTURE'}")
    print("  " + "─" * 80)

    builtin_names = {"hook_punch", "broll_sandwich", "pip_story", "stat_proof",
                     "website_demo", "talking_only", "text_reveal"}

    for d in dirs:
        plan_path = d / "shot_plan.json"
        meta_path = d / "meta.json"
        if not plan_path.exists():
            continue
        plan = json.loads(plan_path.read_text())
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

        label = "★ " if d.name not in builtin_names else "  "
        name_display = d.name + ("" if d.name in builtin_names else " [saved]")
        dur = f"{plan.get('duration_s', 0):.0f}s"
        structure = shot_summary(plan.get("shots", []))
        print(f"{label}{name_display:<22} {dur:<10} {structure}")

    print()
    print("  ★ = your saved templates")
    print()
    print("  Use:  python3 bin/templates.py use <name>")
    print("  Info: python3 bin/templates.py info <name>")
    print()


def cmd_use(args):
    name = args.name
    plan, meta = load_template(name)

    # Backup current shot_plan
    if SHOT_PLAN.exists():
        backup = PUBLIC / "shot_plan_backup.json"
        shutil.copy(SHOT_PLAN, backup)
        print(f"Backed up current plan → public/shot_plan_backup.json")

    with open(SHOT_PLAN, "w") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    desc = meta.get("description", "")
    print(f"\nApplied template: {name}")
    if desc:
        print(f"{desc}")
    print()
    print("Structure:")
    for s in plan["shots"]:
        icon = STYLE_ICONS.get(s["style"], "▪")
        dur = s["end_s"] - s["start_s"]
        extra = ""
        if s["style"] == "cta_closer":
            extra = f" — \"{s.get('cta_text', '')}\" @ {s.get('url', '')}"
        elif s["style"] == "stat_callout":
            extra = f" — {s.get('stat', '')} {s.get('stat_label', '')}"
        elif s["style"] in ("broll_fullscreen", "pip"):
            extra = f" — {s.get('broll_file', 'sport_broll.mp4')}"
        elif s["style"] == "text_cards":
            n = len(s.get("cards", []))
            extra = f" — {n} cards"
        print(f"  {icon} [{s['start_s']:.1f}s–{s['end_s']:.1f}s] {s['style']}{extra}")

    print()
    print("Edit public/shot_plan.json to fill in your content, then:")
    print("  npx remotion still src/index.ts SmartEdit --frame=60 --output=/tmp/test.png && open /tmp/test.png")


def cmd_save(args):
    name = args.name
    if not name.replace("_", "").replace("-", "").isalnum():
        print("ERROR: name must be alphanumeric (underscores/dashes OK)")
        sys.exit(1)

    dest = TEMPLATES_DIR / name
    if dest.exists() and not args.force:
        print(f"ERROR: Template '{name}' already exists. Use --force to overwrite.")
        sys.exit(1)

    if not SHOT_PLAN.exists():
        print("ERROR: public/shot_plan.json not found.")
        sys.exit(1)

    dest.mkdir(exist_ok=True)
    shutil.copy(SHOT_PLAN, dest / "shot_plan.json")

    plan = json.loads(SHOT_PLAN.read_text())
    meta = {
        "name": name,
        "description": args.desc or "Custom saved template",
        "tags": ["custom"],
        "duration_hint": f"{plan.get('duration_s', 0):.0f}s"
    }
    with open(dest / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Saved template: {name}")
    print(f"Location: templates/{name}/")
    structure = shot_summary(plan.get("shots", []))
    print(f"Structure: {structure}")


def cmd_info(args):
    name = args.name
    plan, meta = load_template(name)

    print(f"\n{'='*50}")
    print(f"  {meta.get('name', name)}")
    print(f"{'='*50}")
    if meta.get("description"):
        print(f"  {meta['description']}")
    tags = meta.get("tags", [])
    if tags:
        print(f"  Tags: {', '.join(tags)}")
    print(f"  Duration: {plan.get('duration_s', 0)}s")
    print()
    print("  Shots:")
    for s in plan["shots"]:
        icon = STYLE_ICONS.get(s["style"], "▪")
        dur = s["end_s"] - s["start_s"]
        print(f"    {icon} Shot {s['id']}: {s['style']} [{s['start_s']}s → {s['end_s']}s, {dur:.1f}s]")
        for k, v in s.items():
            if k in ("id", "style", "start_s", "end_s"):
                continue
            print(f"         {k}: {json.dumps(v, ensure_ascii=False)}")
    print()


def cmd_delete(args):
    name = args.name
    builtin = {"hook_punch", "broll_sandwich", "pip_story", "stat_proof",
               "website_demo", "talking_only", "text_reveal"}
    if name in builtin:
        print(f"ERROR: '{name}' is a built-in template and cannot be deleted.")
        sys.exit(1)

    path = TEMPLATES_DIR / name
    if not path.exists():
        print(f"ERROR: Template '{name}' not found.")
        sys.exit(1)

    shutil.rmtree(path)
    print(f"Deleted template: {name}")


def cmd_preview(args):
    name = args.name
    load_template(name)  # validate exists
    cmd_use(args)

    out = f"/tmp/template_preview_{name}.png"
    frame = args.frame
    print(f"\nRendering still at frame {frame}...")
    result = subprocess.run(
        ["npx", "remotion", "still", "src/index.ts", "SmartEdit",
         f"--frame={frame}", f"--output={out}"],
        cwd=PROJECT_ROOT
    )
    if result.returncode == 0:
        subprocess.run(["open", out])
        print(f"Preview: {out}")
    else:
        print("Render failed — check shot_plan.json content.")


def main():
    parser = argparse.ArgumentParser(description="Personal brand video templates")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List all templates")

    p_use = sub.add_parser("use", help="Apply a template to shot_plan.json")
    p_use.add_argument("name")

    p_save = sub.add_parser("save", help="Save current shot_plan as a template")
    p_save.add_argument("name")
    p_save.add_argument("--desc", default="", help="Template description")
    p_save.add_argument("--force", action="store_true", help="Overwrite if exists")

    p_info = sub.add_parser("info", help="Show full template details")
    p_info.add_argument("name")

    p_del = sub.add_parser("delete", help="Delete a saved template")
    p_del.add_argument("name")

    p_prev = sub.add_parser("preview", help="Apply template + render still")
    p_prev.add_argument("name")
    p_prev.add_argument("--frame", type=int, default=60, help="Frame to render (default 60)")

    args = parser.parse_args()

    if not args.cmd or args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "use":
        cmd_use(args)
    elif args.cmd == "save":
        cmd_save(args)
    elif args.cmd == "info":
        cmd_info(args)
    elif args.cmd == "delete":
        cmd_delete(args)
    elif args.cmd == "preview":
        cmd_preview(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
