"""Download a bounded Kaggle COCO sample and candidate count manifest, not training."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import random

from alpha_captcha.kaggle_data import dataset_metadata, fetch_kaggle_file


REF = "awsaf49/coco-2017-dataset"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--per-bin", type=int, default=4, help="per original split and count 0/1/2/3/4/5/6+/crowd")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--splits", nargs="+", choices=["train2017", "val2017"], default=["train2017", "val2017"])
    args = parser.parse_args()
    if not 1 <= args.per_bin <= 100:
        parser.error("per-bin must be 1..100")
    root = args.root.resolve()
    raw = (root / "data/raw/kaggle/coco2017").resolve()
    if not raw.is_relative_to(root / "data/raw/kaggle"):
        raise ValueError("Kaggle data directory resolves outside the permitted raw root")
    raw.mkdir(parents=True, exist_ok=True)
    metadata = dataset_metadata(REF)
    version = metadata["currentVersionNumber"]
    metadata_path = raw / "dataset-metadata.json"
    if metadata_path.exists():
        if json.loads(metadata_path.read_text(encoding="utf-8"))["currentVersionNumber"] != version:
            raise ValueError("cached dataset version differs; use a separate versioned raw directory")
    else:
        with metadata_path.open("x", encoding="utf-8") as output:
            json.dump(metadata, output, ensure_ascii=False, indent=2)
    records = []
    files = []
    buckets_report = {}
    for split in args.splits:
        annotations_path = raw / "annotations" / f"instances_{split}.json"
        result = fetch_kaggle_file(
            REF, f"coco2017/annotations/instances_{split}.json", annotations_path,
            workspace_root=root, max_bytes=600_000_000, expected_kind="json",
        )
        files.append(result)
        print(f"{split}: annotations ready ({result['bytes']} bytes)", flush=True)
        annotations = json.loads(annotations_path.read_text(encoding="utf-8"))
        person_ids = {category["id"] for category in annotations["categories"] if category["name"] == "person"}
        if len(person_ids) != 1:
            raise ValueError("expected exactly one person category")
        person_id = next(iter(person_ids))
        by_image = defaultdict(list)
        for annotation in annotations["annotations"]:
            if annotation["category_id"] == person_id:
                by_image[annotation["image_id"]].append(annotation)
        bins = defaultdict(list)
        for picture in annotations["images"]:
            items = by_image[picture["id"]]
            has_crowd = any(item.get("iscrowd", 0) for item in items)
            count = sum(not item.get("iscrowd", 0) for item in items)
            bucket = "crowd" if has_crowd else str(min(count, 6))
            bins[bucket].append(picture)
        selected = []
        for bucket in sorted(bins):
            candidates = sorted(bins[bucket], key=lambda picture: picture["id"])
            random.Random(f"{args.seed}:{split}:{bucket}").shuffle(candidates)
            selected.extend((picture, bucket) for picture in candidates[:args.per_bin])
        buckets_report[split] = {"available": {key: len(value) for key, value in bins.items()},
                                 "selected": dict(Counter(bucket for _, bucket in selected))}

        def obtain(item):
            picture, bucket = item
            destination = raw / split / picture["file_name"]
            downloaded = fetch_kaggle_file(
                REF, f"coco2017/{split}/{picture['file_name']}", destination,
                workspace_root=root, max_bytes=25_000_000, expected_kind="image",
            )
            objects = by_image[picture["id"]]
            crowd = any(obj.get("iscrowd", 0) for obj in objects)
            boxes = []
            for obj in objects:
                if not obj.get("iscrowd", 0):
                    x, y, width, height = obj["bbox"]
                    boxes.append([x, y, x + width, y + height])
            record = {
                "schema_version": 1, "image_path": destination.relative_to(root).as_posix(),
                "source": "kaggle", "dataset_ref": REF, "dataset_version": version,
                "image_id": str(picture["id"]), "group_id": f"coco:{picture['id']}",
                "parent_id": None, "sha256": downloaded["sha256"], "split": None,
                "original_split": "train" if split == "train2017" else "test",
                "labels": {"tree": None, "building": None, "pond": None},
                "person": {"present": True if objects else None, "count": None,
                           "count_status": "crowd" if crowd else "unknown",
                           "boxes": boxes, "iscrowd": crowd},
                "annotation_person_count": len(boxes), "annotation_bucket": bucket,
                "annotation_review": "pending_visual_review",
                "width": picture["width"], "height": picture["height"],
                "license_id": picture.get("license"),
                "usage_note": "Kaggle COCO mirror; image rights vary by source. COCO non-crowd box count is provisional, not a verified human count. Unannotated objects are unknown.",
            }
            return record, downloaded

        with ThreadPoolExecutor(max_workers=4) as pool:
            for record, downloaded in pool.map(obtain, selected):
                records.append(record)
                files.append(downloaded)
        print(f"{split}: {len(selected)} sample images ready", flush=True)
        del annotations, by_image
    if dataset_metadata(REF)["currentVersionNumber"] != version:
        raise ValueError("dataset version changed during download; refusing a mixed-version manifest")
    from alpha_captcha.dataset import save_jsonl, validate_manifest, grouped_split
    validation = validate_manifest(records, root, verify_files=True)
    manifest_dir = root / "data/manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    output = manifest_dir / "coco-count-candidates.jsonl"
    save_jsonl(records, output, overwrite=True)
    training_candidates = [row for row in records if row["original_split"] == "train"]
    split_records = grouped_split(
        training_candidates, root, ratios=(.85, .15, 0), seed=args.seed,
        respect_original_split=False,
    ) if training_candidates else []
    # Keep the source's official validation pool untouched as development test.
    split_records.extend({**row, "split": "test"} for row in records if row["original_split"] == "test")
    save_jsonl(split_records, manifest_dir / "coco-count-split.jsonl", overwrite=True)
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "dataset_ref": REF,
        "dataset_version": version, "license_name": metadata.get("licenseName"),
        "seed": args.seed, "per_bin": args.per_bin, "buckets": buckets_report,
        "files": files, "validation": validation,
        "split_validation": validate_manifest(split_records, root, verify_files=True, require_split=True),
        "limitations": ["candidate box counts need visual review", "zero annotated person is not automatically a verified zero-person image", "crowd counts unknown", "similar-scene grouping requires further review", "count-stratified sample is not population accuracy data", "school images never accessed"],
    }
    (manifest_dir / "coco-count-preparation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(records), "manifest": str(output), "verified_counts": 0,
                      "note": "Data preparation only; no model training or accuracy measurement."}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
