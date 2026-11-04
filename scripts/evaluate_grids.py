"""Adapt existing pixel prediction reports, then score seeded 4-of-9 val grids."""

import argparse
import json
from pathlib import Path

from alpha_captcha.grid_evaluation import (
    adapt_person_report, adapt_presence_predictions, evaluate_cached_grids, write_new_json,
)
from alpha_captcha.tasks import TaskCondition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("adapt-presence", "adapt-person", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
        command.add_argument("--output", type=Path, required=True, help="new JSON file; no overwrite")
        if name == "evaluate":
            command.add_argument("--cache", type=Path, required=True)
            command.add_argument("--condition", type=Path, required=True, help="public task_type/operator/n JSON only")
            command.add_argument("--grids", type=int, default=1)
            command.add_argument("--seed", type=int, default=42)
            command.add_argument("--mode", choices=["disjoint", "reuse"], default="disjoint")
        else:
            command.add_argument("--report", type=Path, required=True)
            if name == "adapt-presence":
                command.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "adapt-presence":
            result = adapt_presence_predictions(args.manifest, args.predictions, args.report, args.root)
        elif args.action == "adapt-person":
            result = adapt_person_report(args.manifest, args.report, args.root)
        else:
            condition = TaskCondition.from_dict(json.loads(args.condition.read_text(encoding="utf-8-sig")))
            result = evaluate_cached_grids(args.manifest, args.cache, args.root, condition,
                                           grids=args.grids, seed=args.seed, mode=args.mode)
        write_new_json(args.output, result)
        print(json.dumps({key: result[key] for key in ("status", "exact_set", "coverage", "target_achieved") if key in result}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
