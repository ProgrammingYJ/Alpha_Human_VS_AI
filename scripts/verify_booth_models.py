"""Saved-RGB integration check; this is not a browser/OS-click verification.

The fixture builder/evaluator reads private demo labels, then freezes questions
before loading a model. Model inference receives nine PIL images only.
"""

import argparse
import json
from pathlib import Path
import random
import time

from PIL import Image, ImageOps
import torch

from alpha_captcha.inference import TorchTilePredictor
from alpha_captcha.tasks import TaskCondition, select_tiles
from alpha_captcha.tree_model import TreeCountPredictor
from alpha_captcha.timing import plan_click_offsets


def truth(metadata, topic):
    if topic == "person_ge3":
        count = metadata.get("personCount")
        return count >= 3 if type(count) is int else None
    if topic == "tree_ge3":
        value = metadata.get("treeAtLeast3")
        if type(value) is bool:
            return value
        count = metadata.get("treeCount")
        return count >= 3 if type(count) is int else None
    return metadata.get("building" if topic == "building_present" else "pond")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, default=Path("data/booth/demo-bank.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    args = parser.parse_args()
    if args.output.exists():
        parser.error("choose a new output directory")
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    if not bank.get("demoOnly") or bank.get("schoolPhotosUsed") is not False:
        raise ValueError("only the private non-school demo bank is allowed")
    randomizer = random.Random(20261026)
    fixtures = []
    for topic in ("person_ge3", "tree_ge3", "building_present", "pond_present"):
        wanted = randomizer.randint(3 if topic == "tree_ge3" else 2, 4)
        positives = [row for row in bank["images"] if truth(row["labels"], topic) is True]
        negatives = [row for row in bank["images"] if truth(row["labels"], topic) is False]
        selected = randomizer.sample(positives, wanted) + randomizer.sample(negatives, 9 - wanted)
        if len({row["groupId"] for row in selected}) != 9:
            raise ValueError("a fixture may not repeat original capture groups")
        randomizer.shuffle(selected)
        fixtures.append({"topic": topic, "rows": selected,
                         "answer_tiles_for_evaluator_only": [i for i, row in enumerate(selected) if truth(row["labels"], topic)]})
    args.output.mkdir(parents=True)
    # Persist the immutable fixture before any model load or prediction.
    (args.output / "frozen-fixtures.json").write_text(json.dumps(fixtures, ensure_ascii=False, indent=2), encoding="utf-8")
    loading = time.perf_counter()
    predictor = TorchTilePredictor.from_checkpoints(
        "models/checkpoints/presence-limited-v1/presence.pt",
        "models/checkpoints/person-limited-v1/person.pt", device=args.device,
    )
    tree = TreeCountPredictor(device=args.device)
    load_seconds = time.perf_counter() - loading
    results = []
    for fixture in fixtures:
        pixels = []
        for row in fixture["rows"]:
            with Image.open(args.bank.parent / row["file"]) as image:
                canvas = Image.new("RGB", (192, 192), (240, 238, 231))
                fitted = ImageOps.contain(ImageOps.exif_transpose(image).convert("RGB"), (192, 192))
                canvas.paste(fitted, ((192 - fitted.width) // 2, (192 - fitted.height) // 2))
                pixels.append(canvas)
        grid = Image.new("RGB", (592, 592), (255, 255, 255))
        for index, image in enumerate(pixels):
            grid.paste(image, ((index % 3) * 200, (index // 3) * 200))
        grid.save(args.output / (fixture["topic"] + ".png"))
        started = time.perf_counter()
        if fixture["topic"] == "tree_ge3":
            counts = tree.predict_counts(pixels)
            selected = [i for i, count in enumerate(counts) if count >= 3]
            predictions = tree.last_detections
        else:
            condition = (TaskCondition("person_count", "gte", 3) if fixture["topic"] == "person_ge3"
                         else TaskCondition(fixture["topic"]))
            raw = predictor.predict_tiles(pixels)
            threshold = predictor.presence_metadata["profile"]["threshold"]
            selected = select_tiles(raw, condition, dict.fromkeys(("tree", "building", "pond"), threshold))
            predictions = [{"person_count": p.person_count, "presence_scores": dict(p.presence_scores)} for p in raw]
        if args.device == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        result = {"topic": fixture["topic"], "selected_tiles": selected, "predictions": predictions,
                  "evaluator_answer_tiles": fixture["answer_tiles_for_evaluator_only"],
                  "exact_set": set(selected) == set(fixture["answer_tiles_for_evaluator_only"]),
                  "inference_seconds": elapsed, "planned_tile_offsets_seconds": plan_click_offsets(len(selected))}
        results.append(result)
        print(json.dumps({key: result[key] for key in ("topic", "selected_tiles", "exact_set", "inference_seconds")}), flush=True)
    report = {"fixture_seed": 20261026, "model_load_seconds": load_seconds,
              "model_inputs": "nine saved RGB PIL images only; no path or evaluator labels",
              "screen_capture_performed": False, "mouse_control_performed": False,
              "new_accuracy_or_40_percent_validation": False, "school_photos_used": False,
              "tree_model": tree.provenance, "results": results}
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
