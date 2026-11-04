"""Infer an already saved borderless 3x3 RGB grid and plan clicks, never click."""

import argparse
import json
from pathlib import Path
import time

from PIL import Image

from alpha_captcha.geometry import GridLayout
from alpha_captcha.inference import TorchTilePredictor
from alpha_captcha.tasks import TaskCondition
from alpha_captcha.timing import MIN_TILE_INTERVAL_SECONDS, plan_click_offsets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--condition", type=Path, default=Path("configs/task.example.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/pc.example.json"))
    parser.add_argument("--presence", type=Path, default=Path("models/checkpoints/presence-limited-v1/presence.pt"))
    parser.add_argument("--person", type=Path, default=Path("models/checkpoints/person-limited-v1/person.pt"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cpu")
    args = parser.parse_args()
    condition = TaskCondition.from_dict(json.loads(args.condition.read_text(encoding="utf-8-sig")))
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    if config.get("dry_run") is not True:
        raise ValueError("this script only supports dry_run=true")
    grid = GridLayout(**config["grid"])
    if grid.rows != 3 or grid.columns != 3:
        raise ValueError("only a fixed 3x3 grid is supported")
    started = time.perf_counter()
    predictor = TorchTilePredictor.from_checkpoints(args.presence, args.person, device=args.device)
    load_seconds = time.perf_counter() - started
    with Image.open(args.image) as image:
        result = predictor.solve_grid(image, condition)
    clicks = grid.plan(result["selected_tiles"])
    policy = config.get("click_policy", {})
    offsets = plan_click_offsets(len(clicks), policy.get("min_interval_seconds", MIN_TILE_INTERVAL_SECONDS), policy.get("first_click_delay_seconds", 0.0))
    for click, offset in zip(clicks, offsets):
        click["earliest_offset_seconds"] = offset
    result.update(mode="dry-run", task={"task_type": condition.task_type, "operator": condition.operator, "n": condition.n},
                  calibrated=config["screen"]["calibrated"], clicks=clicks,
                  model_loading_seconds=load_seconds, device=args.device,
                  note="Saved image pixels only. Example screen coordinates, provisional first delay, no actual wait/capture/click/submit.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({key: result[key] for key in ("source", "selected_tiles", "clicks", "inference_wall_seconds", "mouse_control_performed")}, indent=2))


if __name__ == "__main__":
    main()
