"""Development manifests and dry-run plans; no mouse or trained model invoked."""

import argparse
import json
from pathlib import Path

from .geometry import GridLayout
from .timing import MIN_TILE_INTERVAL_SECONDS, plan_click_offsets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ALPHA tile-control scaffold")
    commands = parser.add_subparsers(dest="command", required=True)
    dry_run = commands.add_parser("dry-run", help="print manual tile coordinates, without clicking")
    dry_run.add_argument("--config", type=Path, required=True)
    dry_run.add_argument("--tiles", required=True, help="zero-based row-major indices, e.g. 0,4,8")
    check = commands.add_parser("data-check", help="validate Kaggle-only JSONL paths, pixels, hashes and split leakage")
    check.add_argument("--manifest", type=Path, required=True)
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument("--require-split", action="store_true")
    split = commands.add_parser("data-split", help="write a new grouped JSONL development split")
    split.add_argument("--manifest", type=Path, required=True)
    split.add_argument("--root", type=Path, default=Path.cwd())
    split.add_argument("--output", type=Path, required=True)
    split.add_argument("--seed", type=int, default=42)
    split.add_argument("--ratios", default="0.7,0.15,0.15")
    split.add_argument("--ignore-original-split", action="store_true", help="explicitly opt out of pinning all original split assignments")
    args = parser.parse_args(argv)
    try:
        if args.command in {"data-check", "data-split"}:
            from .dataset import grouped_split, load_jsonl, save_jsonl, validate_manifest
            records = load_jsonl(args.manifest)
            if args.command == "data-split":
                records = grouped_split(
                    records, args.root, ratios=tuple(float(x) for x in args.ratios.split(",")),
                    seed=args.seed, respect_original_split=not args.ignore_original_split,
                )
                report = validate_manifest(records, args.root, require_split=True)
                save_jsonl(records, args.output)
                report["output"] = str(args.output)
            else:
                report = validate_manifest(records, args.root, require_split=args.require_split)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        config = json.loads(args.config.read_text(encoding="utf-8-sig"))
        if not isinstance(config, dict):
            raise ValueError("config must be a JSON object")
        if config.get("dry_run") is not True:
            raise ValueError("this scaffold only accepts dry_run=true")
        screen = config["screen"]
        if not isinstance(screen, dict):
            raise ValueError("screen must be a JSON object")
        if type(screen.get("calibrated")) is not bool:
            raise ValueError("screen.calibrated must be a boolean")
        if screen.get("coordinate_system") != "primary-monitor-physical-pixels":
            raise ValueError("only primary-monitor-physical-pixels coordinates are supported")
        if not isinstance(config["grid"], dict):
            raise ValueError("grid must be a JSON object")
        grid = GridLayout(**config["grid"])
        if grid.rows != 3 or grid.columns != 3:
            raise ValueError("the confirmed booth grid is fixed at 3x3")
        parts = args.tiles.split(",")
        if any(not part.strip() for part in parts):
            raise ValueError("--tiles must be a non-empty comma-separated list of integers")
        clicks = grid.plan([int(part.strip()) for part in parts])
        policy = config.get("click_policy", {})
        if not isinstance(policy, dict):
            raise ValueError("click_policy must be an object")
        offsets = plan_click_offsets(
            len(clicks), policy.get("min_interval_seconds", MIN_TILE_INTERVAL_SECONDS),
            policy.get("first_click_delay_seconds", 0.0),
        )
        for click, offset in zip(clicks, offsets):
            click["earliest_offset_seconds"] = offset
        print(json.dumps({
            "mode": "dry-run",
            "source": "manual_tile_indices_no_model",
            "calibrated": screen["calibrated"],
            "note": "Example coordinates only; no screen capture, ML inference or mouse click was performed.",
            "timing": {"min_interval_seconds": policy.get("min_interval_seconds", MIN_TILE_INTERVAL_SECONDS),
                       "first_click_delay_status": "provisional_not_final_booth_rule",
                       "submission_included": False,
                       "assumptions": "No prior click, no processing delay. These are planned offsets, not measured latency."},
            "clicks": clicks,
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
