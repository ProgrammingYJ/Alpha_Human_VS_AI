"""Prepare bounded Kaggle presence candidates; unknown labels never become negatives.

No training or school-photo access is performed. The Outdoors mirror contains
only official training images, so official ADE validation samples come from a
separate full ADE Kaggle mirror. Both mirrors use the same original-image group
identity. Places scene labels are candidate-selection hints, not presence truth.
"""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import random
import urllib.parse
import urllib.request

from PIL import Image
import numpy as np

from alpha_captcha.dataset import grouped_split, save_jsonl, validate_manifest
from alpha_captcha.kaggle_data import dataset_metadata, fetch_kaggle_file


ADE_OUTDOORS = "residentmario/ade20k-outdoors"
ADE_FULL = "awsaf49/ade20k-dataset"
PLACES = "benjaminkz/places365"
PLACE_CLASSES = (
    "pond", "fishpond", "lake-natural", "swimming_pool-outdoor", "river", "waterfall",
)
MASK_RULE = {
    "version": "ade150-positive-only-provisional-v1",
    "tree": {5: "tree", 73: "palm; palm tree"},
    "building": {2: "building; edifice", 26: "house", 49: "skyscraper", 80: "hovel; hut; shack"},
    "person_presence": {13: "person"},
    "absence": "unknown: missing semantic class is never a negative presence label",
    "pond": "unknown: water/lake semantic classes do not establish pond presence",
    "person_count": "unknown: semantic masks are not instance-count annotations",
    "status": "provisional unions; final target inclusion definitions require Kaggle visual review",
}


def safe_child(root: Path, relative: str, prefix: str = "data/raw/kaggle") -> Path:
    """Check before mkdir; resolving the allowed prefix would hide a junction."""
    allowed = root / prefix
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(allowed):
        raise ValueError(f"path escapes permitted {prefix} directory: {relative}")
    return candidate


def write_snapshot(path: Path, value: dict) -> None:
    """Write a provenance snapshot once, preserving all existing originals."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def bounded_json(url: str, max_bytes: int = 2_000_000) -> tuple[dict, dict]:
    request = urllib.request.Request(url, headers={"User-Agent": "Alpha-Captcha-AI/0.1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Kaggle file listing did not return JSON")
        length = response.headers.get("Content-Length")
        if length and int(length) > max_bytes:
            raise ValueError("Kaggle file listing exceeds metadata limit")
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError("Kaggle file listing exceeds metadata limit")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("Kaggle file listing must be an object")
    return value, {"url": url, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def list_images(ref: str, directory: str, pool_size: int, raw: Path) -> tuple[list[dict], dict]:
    """Read a small, explicit prefix pool; do not traverse an entire dataset."""
    entries, pages, token = [], [], None
    while len(entries) < pool_size:
        params = {"path": directory, "pageSize": min(100, pool_size - len(entries))}
        if token:
            params["pageToken"] = token
        url = "https://www.kaggle.com/api/v1/datasets/list-tree/" + ref + "?" + urllib.parse.urlencode(params)
        value, provenance = bounded_json(url)
        pages.append(provenance)
        for item in value.get("files", []):
            remote = item.get("relativeUrl", "")
            path = PurePosixPath(remote)
            if (path.parent.as_posix() == directory and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
                    and ".." not in path.parts and not path.is_absolute()):
                entries.append({"path": remote, "bytes": int(item["totalBytes"])})
        token = value.get("nextPageToken")
        if not token:
            break
        if len(pages) > 4:
            raise ValueError("bounded candidate listing exceeded four pages")
    entries = sorted(entries, key=lambda item: item["path"])[:pool_size]
    snapshot = {
        "dataset_ref": ref, "directory": directory, "selection_pool_limit": pool_size,
        "entries": entries, "pages": pages, "more_files_available": bool(token),
        "limitation": "bounded directory prefix pool, not a random sample of the full dataset",
    }
    name = "file-list-" + hashlib.sha256(directory.encode()).hexdigest()[:16] + ".json"
    write_snapshot(raw / name, snapshot)
    return entries, snapshot


class AssetBudget:
    def __init__(self, root: Path, max_bytes: int, max_files: int):
        self.root, self.max_bytes, self.max_files = root, max_bytes, max_files
        self.files: list[dict] = []
        self.bytes = 0

    def image(self, ref: str, remote: str, destination: Path) -> dict:
        if len(self.files) >= self.max_files or self.bytes >= self.max_bytes:
            raise ValueError("asset file/byte budget exhausted")
        result = fetch_kaggle_file(
            ref, remote, destination, workspace_root=self.root,
            max_bytes=min(2_000_000, self.max_bytes - self.bytes), expected_kind="image",
        )
        self.bytes += result["bytes"]
        result = {**result, "dataset_ref": ref, "local_path": destination.relative_to(self.root).as_posix()}
        self.files.append(result)
        return result

    def class_table(self, destination: Path) -> dict:
        destination = safe_child(self.root, destination.relative_to(self.root).as_posix())
        remote = "ADEChallengeData2016/objectInfo150.txt"
        url = "https://www.kaggle.com/api/v1/datasets/download-raw/" + ADE_FULL + "/" + urllib.parse.quote(remote, safe="")
        if len(self.files) >= self.max_files:
            raise ValueError("asset file budget exhausted")
        limit = min(20_000, self.max_bytes - self.bytes)
        if limit <= 0:
            raise ValueError("asset byte budget exhausted")
        downloaded = False
        if destination.exists():
            if destination.stat().st_size > limit:
                raise ValueError("cached class table exceeds byte limit")
            body = destination.read_bytes()
        else:
            request = urllib.request.Request(url, headers={"User-Agent": "Alpha-Captcha-AI/0.1"})
            with urllib.request.urlopen(request, timeout=45) as response:
                kind = response.headers.get("Content-Type", "").lower()
                if not (kind.startswith("text/") and "html" not in kind):
                    raise ValueError("class table response is not plain text")
                length = response.headers.get("Content-Length")
                if length and int(length) > limit:
                    raise ValueError("class table exceeds byte limit")
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise ValueError("class table exceeds byte limit")
            downloaded = True
        table = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig")), delimiter="\t"))
        names = {int(row["Idx"]): row["Name"].casefold() for row in table}
        expected = {2: "building", 5: "tree", 13: "person", 26: "house", 49: "skyscraper", 73: "palm", 80: "hovel"}
        if len(table) != 150 or any(name not in names.get(index, "") for index, name in expected.items()):
            raise ValueError("ADE class table does not match the provisional mask class rule")
        if downloaded:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(body)
        result = {
            "url": url, "remote_path": remote, "dataset_ref": ADE_FULL,
            "local_path": destination.relative_to(self.root).as_posix(), "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(), "downloaded": downloaded,
        }
        self.files.append(result)
        self.bytes += len(body)
        return result


def source_snapshot(root: Path, ref: str, name: str) -> tuple[Path, dict]:
    raw = safe_child(root, "data/raw/kaggle/" + name)
    metadata = dataset_metadata(ref)
    version = metadata["currentVersionNumber"]
    snapshot = safe_child(root, (raw / "dataset-metadata.json").relative_to(root).as_posix())
    if snapshot.exists():
        previous = json.loads(snapshot.read_text(encoding="utf-8"))
        if previous.get("currentVersionNumber") != version:
            raise ValueError(f"{ref}: cached metadata version differs; keep originals and use a new cache directory")
    elif raw.exists() and any(raw.iterdir()):
        raise ValueError(f"{ref}: nonempty cache has no metadata snapshot; refusing uncertain provenance")
    raw.mkdir(parents=True, exist_ok=True)
    write_snapshot(snapshot, metadata)
    return raw, metadata


def base_record(root: Path, ref: str, metadata: dict, image: Path, downloaded: dict) -> dict:
    with Image.open(image) as picture:
        picture.load()
        width, height = picture.size
    return {
        "schema_version": 1, "image_path": image.relative_to(root).as_posix(),
        "source": "kaggle", "dataset_ref": ref, "dataset_version": metadata["currentVersionNumber"],
        "image_id": image.stem, "group_id": "", "parent_id": None,
        "sha256": downloaded["sha256"], "split": None, "original_split": "train",
        "labels": {"tree": None, "building": None, "pond": None},
        "person": {"present": None, "count": None, "count_status": "unknown", "boxes": None, "iscrowd": False},
        "width": width, "height": height, "source_url": downloaded["url"],
        "source_remote_path": downloaded["remote_path"],
        "license_name": metadata.get("licenseName"), "annotation_review": "pending_visual_review",
        "usage_note": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ade-train", type=int, default=24)
    parser.add_argument("--ade-validation", type=int, default=8)
    parser.add_argument("--places-per-class", type=int, default=4)
    parser.add_argument("--pool-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-bytes", type=int, default=20_000_000, help="hard limit for selected original image/mask/text assets, including cached assets")
    parser.add_argument("--max-files", type=int, default=200)
    args = parser.parse_args()
    if not (1 <= args.ade_train <= 64 and 1 <= args.ade_validation <= 32 and 1 <= args.places_per_class <= 16):
        parser.error("sample sizes must be ADE train 1..64, validation 1..32, Places per class 1..16")
    if not max(args.ade_train, args.ade_validation, args.places_per_class) <= args.pool_size <= 200:
        parser.error("pool-size must cover each requested sample and be at most 200")
    if not 1 <= args.max_bytes <= 20_000_000 or not 1 <= args.max_files <= 200:
        parser.error("max-bytes must be 1..20000000 and max-files 1..200")
    expected_files = 2 * (args.ade_train + args.ade_validation) + len(PLACE_CLASSES) * args.places_per_class + 1
    if expected_files > args.max_files:
        parser.error("requested selected assets exceed max-files")
    root = args.root.resolve()
    if not root.is_dir():
        parser.error("root must be an existing workspace")
    manifest_dir = safe_child(root, "data/manifests", "data/manifests")
    budget = AssetBudget(root, args.max_bytes, args.max_files)
    sources = {}
    for ref, name in ((ADE_OUTDOORS, "presence-ade20k-outdoors"), (ADE_FULL, "presence-ade20k-full"), (PLACES, "presence-places365")):
        sources[ref] = source_snapshot(root, ref, name)
    class_table = budget.class_table(sources[ADE_FULL][0] / "objectInfo150.txt")
    records, selection_pools = [], []
    for ref, original, image_directory, mask_directory, number in (
        (ADE_OUTDOORS, "train", "images/training", "annotations/training", args.ade_train),
        (ADE_FULL, "test", "ADEChallengeData2016/images/validation", "ADEChallengeData2016/annotations/validation", args.ade_validation),
    ):
        raw, metadata = sources[ref]
        image_entries, image_pool = list_images(ref, image_directory, args.pool_size, raw)
        mask_entries, mask_pool = list_images(ref, mask_directory, args.pool_size, raw)
        selection_pools.extend([image_pool, mask_pool])
        masks = {PurePosixPath(item["path"]).stem: item for item in mask_entries}
        candidates = [entry for entry in image_entries if PurePosixPath(entry["path"]).stem in masks]
        random.Random(f"{args.seed}:{ref}:{original}").shuffle(candidates)
        if len(candidates) < number:
            raise ValueError(f"{ref}: bounded pool has only {len(candidates)} paired images/masks, needs {number}")
        for entry in candidates[:number]:
            stem = PurePosixPath(entry["path"]).stem
            local_image = safe_child(root, (raw / entry["path"]).relative_to(root).as_posix())
            mask_entry = masks[stem]
            local_mask = safe_child(root, (raw / mask_entry["path"]).relative_to(root).as_posix())
            image_result = budget.image(ref, entry["path"], local_image)
            mask_result = budget.image(ref, mask_entry["path"], local_mask)
            row = base_record(root, ref, metadata, local_image, image_result)
            with Image.open(local_mask) as mask:
                mask.load()
                if mask.size != (row["width"], row["height"]):
                    raise ValueError(f"mask/image dimensions disagree for {stem}")
                values = np.asarray(mask)
                if values.ndim != 2 or not np.issubdtype(values.dtype, np.integer):
                    raise ValueError(f"expected integer indexed ADE semantic mask for {stem}")
                ids, counts = np.unique(values, return_counts=True)
                if any(int(value) < 0 or int(value) > 150 for value in ids):
                    raise ValueError(f"unexpected semantic class ID for {stem}")
            pixel_counts = dict(zip(map(int, ids), map(int, counts)))
            for label in ("tree", "building"):
                if any(index in pixel_counts for index in MASK_RULE[label]):
                    row["labels"][label] = True
            if 13 in pixel_counts:
                row["person"]["present"] = True
            row.update({
                "group_id": f"ade20k:{stem}", "original_split": original,
                "source_official_split": "training" if original == "train" else "validation",
                "annotation_path": local_mask.relative_to(root).as_posix(),
                "annotation_sha256": mask_result["sha256"], "annotation_source_url": mask_result["url"],
                "annotation_kind": "ade150_semantic_mask", "annotation_pixel_counts": pixel_counts,
                "mask_label_rule": MASK_RULE, "class_table_sha256": class_table["sha256"],
                "candidate_label": {"tree": row["labels"]["tree"], "building": row["labels"]["building"], "pond": None},
                "usage_note": "Kaggle ADE20K mirror; original image rights retained, educational/noncommercial source terms. Positive presence labels use provisional semantic-mask unions only; absent/unsupported labels and exact person counts remain unknown. Pending visual and target-definition review.",
            })
            records.append(row)
        print(f"{ref}: {number} paired {original} candidate images verified", flush=True)
    raw, metadata = sources[PLACES]
    for scene in PLACE_CLASSES:
        entries, pool = list_images(PLACES, "train/" + scene, args.pool_size, raw)
        selection_pools.append(pool)
        random.Random(f"{args.seed}:{PLACES}:{scene}").shuffle(entries)
        if len(entries) < args.places_per_class:
            raise ValueError(f"Places {scene}: insufficient files in bounded pool")
        for entry in entries[:args.places_per_class]:
            local_image = safe_child(root, (raw / entry["path"]).relative_to(root).as_posix())
            image_result = budget.image(PLACES, entry["path"], local_image)
            row = base_record(root, PLACES, metadata, local_image, image_result)
            identity = "places365:" + scene + "/" + local_image.name
            row.update({
                "image_id": scene + "/" + local_image.name, "group_id": identity,
                "source_official_split": "training", "annotation_kind": "scene_label_only",
                "source_scene_label": scene,
                "candidate_label": {"pond": "positive_candidate" if scene in {"pond", "fishpond"} else "hard_negative_candidate"},
                "usage_note": "Kaggle Places365 mirror; image copyrights belong to image owners. Directory scene labels select review candidates only. All presence labels and person counts remain unknown; pond/hard-negative status requires common-guideline visual review.",
            })
            records.append(row)
        print(f"Places {scene}: {args.places_per_class} candidate images verified; presence labels unknown", flush=True)
    for ref, (_, metadata) in sources.items():
        if dataset_metadata(ref)["currentVersionNumber"] != metadata["currentVersionNumber"]:
            raise ValueError(f"{ref}: dataset changed during acquisition; refusing mixed-version manifest")
    validation = validate_manifest(records, root, verify_files=True)
    train_rows = [row for row in records if row["original_split"] == "train"]
    split_rows = grouped_split(train_rows, root, ratios=(0.85, 0.15, 0.0), seed=args.seed, respect_original_split=False)
    split_rows.extend({**row, "split": "test"} for row in records if row["original_split"] == "test")
    split_validation = validate_manifest(split_rows, root, verify_files=True, require_split=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = safe_child(root, "data/manifests/presence-candidates.jsonl", "data/manifests")
    split_path = safe_child(root, "data/manifests/presence-split.jsonl", "data/manifests")
    report_path = safe_child(root, "data/manifests/preparation-report.json", "data/manifests")
    save_jsonl(records, candidate_path, overwrite=True)
    save_jsonl(split_rows, split_path, overwrite=True)
    summary = {
        "records": len(records), "selected_asset_files": len(budget.files), "selected_asset_bytes": budget.bytes,
        "new_download_bytes": sum(item["bytes"] for item in budget.files if item["downloaded"]),
        "masked_positive_labels": {label: sum(row["labels"][label] is True for row in records) for label in ("tree", "building")},
        "mask_person_presence_positive": sum(row["person"]["present"] is True for row in records),
        "pending_visual_review": sum(row["annotation_review"] == "pending_visual_review" for row in records),
        "verified_person_counts": 0, "pond_presence_verified": 0,
        "scene_candidate_counts": dict(Counter(row.get("source_scene_label") for row in records if row.get("source_scene_label"))),
    }
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "summary": summary,
        "seed": args.seed, "sample_limits": {"ade_train": args.ade_train, "ade_validation": args.ade_validation,
            "places_per_class": args.places_per_class, "pool_size": args.pool_size,
            "max_asset_bytes": args.max_bytes, "max_asset_files": args.max_files},
        "dataset_versions": {ref: metadata["currentVersionNumber"] for ref, (_, metadata) in sources.items()},
        "files": budget.files, "selection_pools": selection_pools,
        "metadata_response_bytes": "not included in selected original asset budget; each list response separately limited to 2 MB",
        "class_table": class_table, "mask_label_rule": MASK_RULE,
        "validation": validation, "split_validation": split_validation,
        "split_policy": "official ADE validation -> test; source training candidates group-split 85:15 train/val; no source train image added to test",
        "limitations": [
            "candidate presence positives use provisional mask unions and need target-definition/visual review",
            "no negative presence labels established; unsupported/absent labels remain unknown",
            "Places pond and hard-negative directories are scene hints, not verified presence labels",
            "semantic person masks do not provide exact instance counts",
            "Outdoors mirror has no official validation; those eight samples use a separate full ADE Kaggle mirror",
            "selection comes from bounded listing prefix pools, not population-representative data",
            "similar-scene/burst grouping and near-duplicate inspection remain pending",
            "school images never accessed; no model training or accuracy measurement",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
