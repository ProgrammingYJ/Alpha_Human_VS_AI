"""Kaggle-only development manifests and deterministic leakage-safe splits.

Schema version 1 uses workspace-relative POSIX image paths. ``labels`` contains
tree/building/pond as booleans or null (unannotated). ``person`` contains
``present`` (bool|null), ``count`` (nonnegative int|null), ``count_status``
(verified/unknown/crowd), ``boxes`` (pixel xyxy lists|null), and ``iscrowd``.
Boxes describe individual non-crowd people; a crowd region is never one person.
Verified counts and boxes, when both available, must agree. This module never
infers labels from image filenames and never changes original image files.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import random
import re
from typing import Any


SCHEMA_VERSION = 1
LABELS = ("tree", "building", "pond")
SPLITS = ("train", "val", "test")
ALLOWED_IMAGE_ROOTS = ("data/raw/kaggle", "data/processed/kaggle")
ManifestRecord = dict[str, Any]


class ManifestError(ValueError):
    """A manifest would violate its schema or development-data boundary."""


def sha256_file(path: Path | str) -> str:
    """Hash bytes without loading a complete image into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_jsonl(path: Path | str) -> list[ManifestRecord]:
    """Read JSON objects, allowing blank lines and an optional UTF-8 BOM.

    Loading does not establish trust: call ``validate_manifest`` before using
    records. JSON syntax errors include the source line in their message.
    """
    result = []
    with Path(path).open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line, object_pairs_hook=_unique_json_keys)
            except ValueError as error:
                raise ManifestError(f"{path}:{line_number}: {error}") from error
            if not isinstance(record, dict):
                raise ManifestError(f"{path}:{line_number}: expected a JSON object")
            result.append(record)
    return result


def save_jsonl(
    records: Iterable[ManifestRecord], path: Path | str, *, overwrite: bool = False
) -> None:
    """Write a new JSONL manifest; existing files are protected by default."""
    path = Path(path)
    if path.suffix.lower() != ".jsonl":
        raise ManifestError("manifest output must have a .jsonl extension")
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) for row in records]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as stream:
        for line in lines:
            stream.write(line + "\n")


def _text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{key} must be a non-empty string")
    return value


def _image_path(value: str, workspace_root: Path) -> Path:
    # Reject traversal lexically as well as after resolving symlinks/junctions.
    if "\\" in value or ":" in value:
        raise ManifestError("image_path must use a relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or value != relative.as_posix():
        raise ManifestError("image_path must be canonical and workspace-relative; traversal is forbidden")
    if any(part.casefold() == "school" for part in relative.parts):
        raise ManifestError("school image paths are forbidden in development manifests")
    allowed = [workspace_root / prefix for prefix in ALLOWED_IMAGE_ROOTS]
    candidate = workspace_root.joinpath(*relative.parts)
    if not any(candidate.is_relative_to(prefix) for prefix in allowed):
        raise ManifestError(f"image_path must be under one of {ALLOWED_IMAGE_ROOTS}")
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as error:
        raise ManifestError(f"image_path cannot be safely resolved: {error}") from error
    # The prefixes are intentionally not resolved: a Kaggle root itself must
    # not be a symlink/junction pointing into school data or outside workspace.
    if not any(resolved.is_relative_to(prefix) for prefix in allowed):
        raise ManifestError("image_path symlink/junction escapes the permitted Kaggle roots")
    return resolved


def _person(person: Any, size: tuple[int, int] | None) -> None:
    if not isinstance(person, dict):
        raise ManifestError("person must be an object")
    required = {"present", "count", "count_status", "boxes", "iscrowd"}
    if not required.issubset(person):
        raise ManifestError(f"person is missing fields: {sorted(required - person.keys())}")
    present, count = person["present"], person["count"]
    if present is not None and type(present) is not bool:
        raise ManifestError("person.present must be bool or null")
    if type(person["iscrowd"]) is not bool:
        raise ManifestError("person.iscrowd must be bool")
    status = person["count_status"]
    if status not in ("verified", "unknown", "crowd"):
        raise ManifestError("person.count_status must be verified, unknown or crowd")
    if status == "verified":
        if type(count) is not int or count < 0:
            raise ManifestError("verified person.count must be a nonnegative integer (not bool)")
        if person["iscrowd"]:
            raise ManifestError("crowd annotations cannot have a verified exact count")
        if present is not (count >= 1):
            raise ManifestError("verified person.present must agree with count >= 1")
    elif count is not None:
        raise ManifestError("unknown/crowd person.count must be null, never inferred from boxes")
    if person["iscrowd"] != (status == "crowd"):
        raise ManifestError("person.iscrowd requires count_status=crowd and vice versa")
    if person["iscrowd"] and present is False:
        raise ManifestError("a person crowd cannot have present=false")
    boxes = person["boxes"]
    if boxes is None:
        return
    if not isinstance(boxes, list):
        raise ManifestError("person.boxes must be a list of pixel xyxy boxes or null")
    seen_boxes = set()
    for box in boxes:
        if not isinstance(box, list) or len(box) != 4:
            raise ManifestError("each person box must be [x1,y1,x2,y2]")
        if any(type(number) not in (int, float) or not math.isfinite(number) for number in box):
            raise ManifestError("person box coordinates must be finite numbers (not bool)")
        x1, y1, x2, y2 = box
        if not (0 <= x1 < x2 and 0 <= y1 < y2):
            raise ManifestError("person boxes must have positive area and nonnegative coordinates")
        if size is not None and (x2 > size[0] or y2 > size[1]):
            raise ManifestError("person box extends beyond the image")
        if tuple(box) in seen_boxes:
            raise ManifestError("duplicate person box")
        seen_boxes.add(tuple(box))
    if boxes and present is False:
        raise ManifestError("person boxes contradict present=false")
    if status == "verified" and count != len(boxes):
        raise ManifestError("verified person.count disagrees with the complete individual boxes")


def _components(records: Sequence[ManifestRecord]) -> list[list[int]]:
    """Union declared groups, exact copies, source IDs and parent lineages."""
    parents = list(range(len(records)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    seen: dict[tuple[str, ...], int] = {}
    for index, row in enumerate(records):
        keys = [
            ("group", row["group_id"]),
            ("sha256", row["sha256"]),
            ("path", row["image_path"]),
            ("source_image", row["dataset_ref"], row["image_id"]),
        ]
        if row.get("parent_id"):
            keys.append(("source_image", row["dataset_ref"], row["parent_id"]))
        for key in keys:
            if key in seen:
                parents[find(index)] = find(seen[key])
            else:
                seen[key] = index
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        groups[find(index)].append(index)
    return list(groups.values())


def _leakage_check(records: Sequence[ManifestRecord]) -> list[list[int]]:
    groups = _components(records)
    for group in groups:
        splits = {records[index].get("split") for index in group} - {None}
        if len(splits) > 1:
            ids = [records[index]["image_id"] for index in group[:5]]
            raise ManifestError(f"cross-split leakage in related images {ids}: {sorted(splits)}")
    return groups


def validate_manifest(
    records: Sequence[ManifestRecord],
    workspace_root: Path | str,
    *,
    verify_files: bool = True,
    require_split: bool = False,
) -> dict[str, Any]:
    """Validate development-only records and return coverage/group statistics.

    By default, hash actual bytes, decode each image, check box dimensions and
    reject school/outside paths. ``verify_files=False`` is a schema/path-only
    check; its report explicitly states that bytes and pixels were not checked.
    This validates provenance declarations, not the truth of manual labels.
    """
    root = Path(workspace_root).resolve()
    if not root.is_dir():
        raise ManifestError(f"workspace_root is not a directory: {root}")
    if not records:
        raise ManifestError("manifest has no images")
    identities = set()
    for index, row in enumerate(records, 1):
        try:
            if not isinstance(row, dict):
                raise ManifestError("record must be an object")
            if type(row.get("schema_version")) is not int or row["schema_version"] != SCHEMA_VERSION:
                raise ManifestError(f"schema_version must be {SCHEMA_VERSION}")
            if row.get("source") != "kaggle":
                raise ManifestError("development source must be kaggle; school data is forbidden")
            for field in ("image_path", "dataset_ref", "image_id", "group_id", "sha256", "usage_note"):
                _text(row, field)
            version = row.get("dataset_version")
            if not ((isinstance(version, str) and version.strip()) or (type(version) is int and version > 0)):
                raise ManifestError("dataset_version must be a non-empty string or positive integer")
            if not re.fullmatch(r"[^/\s]+/[^/\s]+", row["dataset_ref"]):
                raise ManifestError("dataset_ref must be owner/dataset-slug")
            if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
                raise ManifestError("sha256 must contain 64 lowercase hexadecimal characters")
            if row.get("parent_id") is not None:
                _text(row, "parent_id")
                if row["parent_id"] == row["image_id"]:
                    raise ManifestError("parent_id must differ from image_id")
            identity = (row["dataset_ref"], str(version), row["image_id"])
            if identity in identities:
                raise ManifestError(f"duplicate dataset/version/image_id: {identity}")
            identities.add(identity)
            for field in ("split", "original_split"):
                if row.get(field) is not None and row[field] not in SPLITS:
                    raise ManifestError(f"{field} must be train, val, test or null")
            if require_split and row.get("split") not in SPLITS:
                raise ManifestError("every image requires an assigned split")
            labels = row.get("labels")
            if not isinstance(labels, dict) or set(labels) != set(LABELS):
                raise ManifestError(f"labels must contain exactly {LABELS}")
            for field, value in labels.items():
                if value is not None and type(value) is not bool:
                    raise ManifestError(f"labels.{field} must be bool or null; unknown is not false")
            image_path = _image_path(row["image_path"], root)
            size = None
            if verify_files:
                if not image_path.is_file():
                    raise ManifestError(f"image file does not exist: {row['image_path']}")
                if sha256_file(image_path) != row["sha256"]:
                    raise ManifestError(f"sha256 mismatch: {row['image_path']}")
                try:
                    from PIL import Image

                    with Image.open(image_path) as image:
                        image.load()
                        size = image.size
                except ImportError as error:
                    raise ManifestError("Pillow is required to verify image pixels") from error
                except (OSError, ValueError, Image.DecompressionBombError) as error:
                    raise ManifestError(f"unreadable image {row['image_path']}: {error}") from error
            _person(row.get("person"), size)
        except (ManifestError, OSError) as error:
            raise ManifestError(f"record {index}: {error}") from error
    _leakage_check(records)
    report = manifest_stats(records)
    report["verification"] = {
        "schema_and_paths": True,
        "file_hashes_and_pixels": verify_files,
        "all_splits_assigned": all(row.get("split") in SPLITS for row in records),
        "label_truth_verified": False,
        "near_duplicate_search_performed": False,
    }
    return report


def _coverage(records: Sequence[ManifestRecord]) -> dict[str, Any]:
    def counts(values: Iterable[bool | None]) -> dict[str, int]:
        values = Counter("unknown" if value is None else "positive" if value else "negative" for value in values)
        return {key: values[key] for key in ("positive", "negative", "unknown")}

    return {
        "labels": {label: counts(row["labels"][label] for row in records) for label in LABELS},
        "person_presence": counts(row["person"]["present"] for row in records),
        "person_count_status": {status: sum(row["person"]["count_status"] == status for row in records)
                                for status in ("verified", "unknown", "crowd")},
        "verified_count_histogram": dict(sorted(Counter(
            str(row["person"]["count"]) for row in records if row["person"]["count_status"] == "verified"
        ).items(), key=lambda pair: int(pair[0]))),
    }


def manifest_stats(records: Sequence[ManifestRecord]) -> dict[str, Any]:
    """Summarize already schema-valid rows; no class coverage is promised."""
    groups = _components(records)
    split_stats = {}
    warnings = []
    for split in (*SPLITS, "unassigned"):
        subset = [row for row in records if (row.get("split") or "unassigned") == split]
        split_stats[split] = {"images": len(subset), "groups": len(_components(subset)), **_coverage(subset)}
        if split in SPLITS:
            if not subset:
                warnings.append(f"{split}: no images; group constraints do not guarantee coverage")
            else:
                for label, coverage in split_stats[split]["labels"].items():
                    if not coverage["positive"] or not coverage["negative"]:
                        warnings.append(f"{split}: {label} lacks an annotated positive or negative class")
                if not split_stats[split]["person_count_status"]["verified"]:
                    warnings.append(f"{split}: no verified person counts")
    hashes = Counter(row["sha256"] for row in records)
    return {
        "images": len(records),
        "groups": len(groups),
        "declared_group_ids": len({row["group_id"] for row in records}),
        "duplicate_hash_groups": sum(number > 1 for number in hashes.values()),
        "duplicate_hash_extra_images": sum(number - 1 for number in hashes.values()),
        "datasets": dict(sorted(Counter(f"{row['dataset_ref']}@{row['dataset_version']}" for row in records).items())),
        **_coverage(records),
        "splits": split_stats,
        "warnings": warnings,
    }


def grouped_split(
    records: Sequence[ManifestRecord],
    workspace_root: Path | str,
    *,
    ratios: Sequence[float] = (0.7, 0.15, 0.15),
    seed: int = 42,
    respect_original_split: bool = True,
    verify_files: bool = True,
) -> list[ManifestRecord]:
    """Return copied rows split by connected lineage, never individual images.

    Official ``original_split`` values, if respected, pin the whole connected
    group. Contradictory official assignments are rejected rather than silently
    changed. Unpinned groups are balanced approximately by image count. Large
    groups and pinned rows can prevent requested ratios or class coverage.
    Ordering of input rows does not change image assignments. Originals and
    supplied dictionaries are never modified.
    """
    if len(ratios) != 3 or any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in ratios):
        raise ManifestError("ratios must contain three finite nonnegative numbers")
    if not math.isclose(sum(ratios), 1.0, abs_tol=1e-9):
        raise ManifestError("train/val/test ratios must sum to 1")
    if type(seed) is not int:
        raise ManifestError("seed must be an integer (not bool)")
    if type(respect_original_split) is not bool:
        raise ManifestError("respect_original_split must be bool")
    validate_manifest(records, workspace_root, verify_files=verify_files)
    result = deepcopy(list(records))
    groups = _components(result)
    counts = dict.fromkeys(SPLITS, 0)
    pending = []
    for group in groups:
        official = {result[index].get("original_split") for index in group} - {None}
        if respect_original_split and len(official) > 1:
            raise ManifestError(f"related images span contradictory official splits: {sorted(official)}")
        if respect_original_split and official:
            split = next(iter(official))
            for index in group:
                result[index]["split"] = split
            counts[split] += len(group)
        else:
            pending.append(group)
    # Stable key before seeded shuffling makes assignments input-order invariant.
    pending.sort(key=lambda group: sorted(
        (result[index]["dataset_ref"], str(result[index]["dataset_version"]), result[index]["image_id"])
        for index in group
    ))
    random.Random(seed).shuffle(pending)
    pending.sort(key=len, reverse=True)
    targets = {split: len(result) * ratio for split, ratio in zip(SPLITS, ratios)}
    active = [split for split, ratio in zip(SPLITS, ratios) if ratio > 0]
    for group in pending:
        size = len(group)
        split = min(active, key=lambda name: (counts[name] + size - targets[name]) ** 2 - (counts[name] - targets[name]) ** 2)
        for index in group:
            result[index]["split"] = split
        counts[split] += size
    _leakage_check(result)
    return result
