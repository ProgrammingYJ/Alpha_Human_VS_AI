"""Before first fitting, add independent Kaggle water-scene heldout candidates."""

from copy import deepcopy
import json
from pathlib import Path
import random

from alpha_captcha.dataset import load_jsonl, save_jsonl, validate_manifest
from alpha_captcha.kaggle_data import dataset_metadata, fetch_kaggle_file
from prepare_presence_candidates import list_images, safe_child


def main():
    root = Path(__file__).resolve().parents[1]
    originals = load_jsonl(root / "data/manifests/presence-split.jsonl")
    places = [row for row in originals if row["dataset_ref"] == "benjaminkz/places365"]
    raw = safe_child(root, "data/raw/kaggle/presence-places365")
    metadata = dataset_metadata("benjaminkz/places365")
    if metadata["currentVersionNumber"] != places[0]["dataset_version"]:
        raise ValueError("Places version changed")
    existing = {row["image_id"] for row in places}
    records, files = [], []
    for scene, count in [("pond", 4), ("fishpond", 2), ("lake-natural", 2),
                         ("swimming_pool-outdoor", 2), ("river", 2), ("waterfall", 2)]:
        candidates, _ = list_images("benjaminkz/places365", f"train/{scene}", 128, raw)
        candidates = [item for item in candidates if scene + "/" + Path(item["path"]).name not in existing]
        random.Random(f"42:heldout-v1:{scene}").shuffle(candidates)
        for index, item in enumerate(candidates[:count]):
            destination = safe_child(root, (raw / item["path"]).relative_to(root).as_posix())
            downloaded = fetch_kaggle_file("benjaminkz/places365", item["path"], destination,
                                            workspace_root=root, max_bytes=2_000_000, expected_kind="image")
            row = deepcopy(places[0])
            image_id = scene + "/" + destination.name
            from PIL import Image
            with Image.open(destination) as image:
                width, height = image.size
            row.update(image_path=destination.relative_to(root).as_posix(), image_id=image_id,
                       group_id="places365:" + image_id, sha256=downloaded["sha256"],
                       split="val" if index % 2 == 0 else "test", width=width, height=height,
                       source_remote_path=item["path"], source_url=downloaded["url"],
                       source_scene_label=scene, candidate_label={"pond": "review_required"},
                       acquisition_purpose="pre-fit heldout class coverage, not model-driven selection")
            records.append(row)
            files.append(downloaded)
    if len(records) != 14:
        raise ValueError("expected exactly 14 independent additional candidates")
    combined = validate_manifest(originals + records, root, require_split=True)
    save_jsonl(records, root / "data/manifests/presence-extra-heldout.jsonl", overwrite=True)
    report = {"reason": "original heldout sets lack verified pond positives, identified before any model fit/prediction",
              "selection_seed": 42, "new_images": len(records), "bytes": sum(item["bytes"] for item in files),
              "files": files, "combined_validation": combined, "all_labels_pending_review": True,
              "original_splits_changed": False, "school_data_used": False}
    (root / "data/manifests/presence-extra-heldout-preparation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"new_images": len(records), "bytes": report["bytes"], "original_splits_changed": False}), flush=True)


if __name__ == "__main__":
    main()
