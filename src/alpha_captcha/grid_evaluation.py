"""Score seeded 4-positive/5-negative validation grids using pixel predictions.

Truth constructs/channels the evaluator only. Cached predictions enter
select_tiles without truth labels or the number of correct tiles. Local hashes
detect inconsistent inputs; unsigned caches cannot prove authentic ML execution.
"""

from collections import Counter, defaultdict
from collections.abc import Mapping
import hashlib
import json
import math
from pathlib import Path
import random

from .dataset import _components, load_jsonl, sha256_file, validate_manifest
from .tasks import TaskCondition, TilePrediction, select_tiles


CACHE_KIND = "alpha_captcha_pixel_predictions_v1"
TARGET_RATE = 0.4
POSITIVE_TILES = 4
NEGATIVE_TILES = 5
UNSIGNED_NOTICE = (
    "Unsigned local cache: hashes verify file/manifest consistency, not that an "
    "honest pixel-only model actually generated these predictions."
)


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_keys)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _identity(row):
    return row["dataset_ref"], str(row["dataset_version"]), row["image_id"]


def _require_val(split):
    if split != "val":
        raise ValueError("development grid evaluation accepts val only; old test is not a tuning fallback")


def _manifest(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    digest = sha256_file(path)
    records = load_jsonl(path)
    validate_manifest(records, root, require_split=True)
    if sha256_file(path) != digest:
        raise ValueError("manifest changed while loading")
    return records, root, digest


def _file_entry(path, root, role):
    path = Path(path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"{role} must be an existing workspace file")
    return {"role": role, "path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}


def _prediction_row(row, *, scores=None, count=None):
    prediction = TilePrediction(presence_scores=scores or {}, person_count=count)
    return {
        **{key: row[key] for key in ("dataset_ref", "dataset_version", "image_id", "image_path", "sha256", "source", "group_id", "split")},
        "presence_scores": dict(prediction.presence_scores), "person_count": prediction.person_count,
    }


def _cache(manifest_hash, split, predictions, files, thresholds, source_format):
    return {
        "schema_version": 1, "kind": CACHE_KIND, "manifest_sha256": manifest_hash,
        "split": split, "source_format": source_format, "provenance_files": files,
        "thresholds": thresholds, "predictions": predictions,
        "predictions_sha256": _digest(predictions), "authenticity_notice": UNSIGNED_NOTICE,
    }


def _threshold(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("a finite frozen probability threshold is required")
    return float(value)


def adapt_presence_predictions(manifest_path, predictions_path, report_path, workspace_root, *, split="val"):
    _require_val(split)
    records, root, manifest_hash = _manifest(manifest_path, workspace_root)
    report = _read_json(report_path)
    if report.get("manifest_sha256") != manifest_hash or report.get("school_data_used") is not False:
        raise ValueError("presence report must match the Kaggle manifest and declare no school data")
    threshold = _threshold(report["profile"]["threshold"])
    checkpoint = Path(report["checkpoint"])
    if not checkpoint.is_absolute():
        checkpoint = root / checkpoint
    checkpoint_file = _file_entry(checkpoint, root, "checkpoint")
    if checkpoint_file["sha256"] != report.get("checkpoint_sha256"):
        raise ValueError("presence checkpoint hash differs from its report")
    raw_predictions = _read_json(predictions_path)
    if not isinstance(raw_predictions, list):
        raise ValueError("presence predictions must be a JSON array")
    index = defaultdict(list)
    for row in records:
        index[(row["image_id"], row["image_path"])].append(row)
    predictions, seen = [], set()
    for raw in raw_predictions:
        matches = index[(raw["image_id"], raw["image_path"])]
        if len(matches) != 1:
            raise ValueError("unknown or ambiguous presence prediction identity")
        row = matches[0]
        if row["split"] != split or raw.get("split") != split or _identity(row) in seen:
            raise ValueError("presence prediction has wrong split or duplicate identity")
        seen.add(_identity(row))
        scores = raw["scores"]
        if not isinstance(scores, Mapping) or set(scores) != {"tree", "building", "pond"}:
            raise ValueError("presence prediction needs exactly three class scores")
        # Evaluator labels/decisions in source reports are never used as predictions.
        predictions.append(_prediction_row(row, scores=scores))
    files = [_file_entry(report_path, root, "report"), _file_entry(predictions_path, root, "predictions"), checkpoint_file]
    return _cache(manifest_hash, split, predictions, files, dict.fromkeys(("tree", "building", "pond"), threshold), "presence_v1")


def adapt_person_report(manifest_path, report_path, workspace_root, *, split="val"):
    _require_val(split)
    records, root, manifest_hash = _manifest(manifest_path, workspace_root)
    report = _read_json(report_path)
    metadata = report["metadata"]
    if metadata.get("manifest_sha256") != manifest_hash or metadata.get("school_data_used") is not False:
        raise ValueError("person report must match the Kaggle manifest and declare no school data")
    checkpoint_file = _file_entry(Path(report_path).resolve().parent / "person.pt", root, "checkpoint")
    if checkpoint_file["sha256"] != metadata.get("checkpoint_sha256"):
        raise ValueError("person checkpoint hash differs from its report")
    index = defaultdict(list)
    for row in records:
        index[(row["image_id"], row["sha256"])].append(row)
    predictions, seen = [], set()
    for raw in report["evaluation"][split]["predictions"]:
        matches = index[(raw["image_id"], raw["sha256"])]
        if len(matches) != 1:
            raise ValueError("unknown or ambiguous person prediction identity/hash")
        row = matches[0]
        if row["split"] != split or _identity(row) in seen:
            raise ValueError("person prediction has wrong split or duplicate identity")
        seen.add(_identity(row))
        # actual_count is deliberately ignored; truth comes from the manifest.
        predictions.append(_prediction_row(row, count=raw["person_count"]))
    return _cache(manifest_hash, split, predictions,
                  [_file_entry(report_path, root, "report"), checkpoint_file], {}, "person_v1")


def validate_prediction_cache(cache, records, workspace_root, manifest_hash, *, split="val"):
    _require_val(split)
    root = Path(workspace_root).resolve()
    if not isinstance(cache, dict) or type(cache.get("schema_version")) is not int or cache.get("schema_version") != 1 or cache.get("kind") != CACHE_KIND:
        raise ValueError("unsupported prediction cache schema")
    if cache.get("manifest_sha256") != manifest_hash or cache.get("split") != split:
        raise ValueError("cache manifest hash/split mismatch")
    predictions = cache.get("predictions")
    if not isinstance(predictions, list) or cache.get("predictions_sha256") != _digest(predictions):
        raise ValueError("prediction cache payload hash mismatch")
    files = cache.get("provenance_files")
    required_roles = {"report", "checkpoint", "predictions"} if cache.get("source_format") == "presence_v1" else {"report", "checkpoint"}
    if cache.get("source_format") not in {"presence_v1", "person_v1"} or not isinstance(files, list) or any(not isinstance(entry, dict) for entry in files) or {entry.get("role") for entry in files} != required_roles or len(files) != len(required_roles):
        raise ValueError("cache provenance files are missing or duplicated")
    for entry in files:
        value = entry["path"]
        if not isinstance(value, str) or "\\" in value or ":" in value or Path(value).is_absolute() or ".." in Path(value).parts:
            raise ValueError("cache provenance paths must be workspace-relative")
        actual = _file_entry(root / value, root, entry["role"])
        if actual["sha256"] != entry["sha256"]:
            raise ValueError("cache source/checkpoint file hash changed")
    thresholds = cache.get("thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) - {"tree", "building", "pond"}:
        raise ValueError("cache thresholds must be a presence-label mapping")
    for value in thresholds.values():
        _threshold(value)
    manifest_index = {_identity(row): row for row in records}
    result = {}
    fields = ("image_path", "sha256", "source", "group_id", "split")
    for prediction in predictions:
        identity = _identity(prediction)
        row = manifest_index.get(identity)
        if row is None or identity in result or row["split"] != split or any(prediction.get(key) != row[key] for key in fields):
            raise ValueError("cache row identity/hash/source/group/split differs from manifest")
        result[identity] = TilePrediction(
            presence_scores=prediction.get("presence_scores", {}), person_count=prediction.get("person_count"),
        )
    return result


def _truth(row, condition):
    if condition.task_type in {"tree_present", "building_present", "pond_present"}:
        return row["labels"][condition.task_type.removesuffix("_present")]
    person = row["person"]
    if person["iscrowd"]:
        return None
    if condition.task_type == "person_present":
        return person["present"]
    if person["count_status"] != "verified" or person["count"] is None:
        return None
    return person["count"] == condition.n if condition.operator == "eq" else person["count"] >= condition.n


def plan_validation_grids(records, condition, *, seed=42, grids=1, mode="disjoint", split="val"):
    """Select from truth + seed only, before seeing any prediction values."""
    _require_val(split)
    if not isinstance(condition, TaskCondition):
        raise ValueError("condition must be a TaskCondition")
    if type(seed) is not int or type(grids) is not int or grids <= 0 or mode not in {"disjoint", "reuse"}:
        raise ValueError("seed/grids must be integers and mode must be disjoint or reuse")
    components = _components(records)  # Same parent/hash/source lineage rules as manifest leakage validation.
    pools, unknown = {}, 0
    for component_number, component in enumerate(components):
        pool = {True: [], False: []}
        for index in component:
            row = records[index]
            if row["split"] != split:
                continue
            truth = _truth(row, condition)
            if truth is None:
                unknown += 1
            else:
                pool[truth].append(row)
        if pool[True] or pool[False]:
            for candidates in pool.values():
                candidates.sort(key=_identity)
            pools[component_number] = pool
    positive_only = [key for key, pool in pools.items() if pool[True] and not pool[False]]
    negative_only = [key for key, pool in pools.items() if pool[False] and not pool[True]]
    mixed = [key for key, pool in pools.items() if pool[True] and pool[False]]
    capacity = min((len(positive_only) + len(mixed)) // POSITIVE_TILES,
                   (len(negative_only) + len(mixed)) // NEGATIVE_TILES,
                   len(pools) // 9)
    randomizer = random.Random(seed)

    def choose_groups(number):
        positives, negatives, both = positive_only.copy(), negative_only.copy(), mixed.copy()
        randomizer.shuffle(positives)
        randomizer.shuffle(negatives)
        randomizer.shuffle(both)
        positives = positives[:POSITIVE_TILES * number]
        negatives = negatives[:NEGATIVE_TILES * number]
        positive_gap = POSITIVE_TILES * number - len(positives)
        positives.extend(both[:positive_gap])
        negatives.extend(both[positive_gap:positive_gap + NEGATIVE_TILES * number - len(negatives)])
        return positives, negatives

    result = []
    count = min(grids, capacity) if mode == "disjoint" else grids if capacity else 0
    positive_groups, negative_groups = choose_groups(count) if mode == "disjoint" else ([], [])
    for grid_number in range(count):
        if mode == "reuse":
            positive_groups, negative_groups = choose_groups(1)
            offset = 0
        else:
            offset = grid_number
        entries = []
        for truth, groups_for_role, per_grid in ((True, positive_groups, POSITIVE_TILES), (False, negative_groups, NEGATIVE_TILES)):
            for group in groups_for_role[offset * per_grid:(offset + 1) * per_grid]:
                row = randomizer.choice(pools[group][truth])
                entries.append({"identity": list(_identity(row)), "component": group, "truth": truth})
        randomizer.shuffle(entries)
        result.append({"tiles": entries, "answer_tiles": [index for index, entry in enumerate(entries) if entry["truth"]]})
    return {
        "seed": seed, "split": split, "mode": mode, "requested_grids": grids,
        "positive_tiles_per_grid": POSITIVE_TILES, "negative_tiles_per_grid": NEGATIVE_TILES,
        "available_disjoint_grids": capacity, "known_positive_images": sum(len(pool[True]) for pool in pools.values()),
        "known_negative_images": sum(len(pool[False]) for pool in pools.values()), "unknown_images_excluded": unknown,
        "positive_groups": len(positive_only) + len(mixed), "negative_groups": len(negative_only) + len(mixed),
        "grids": result,
    }


def evaluate_cached_grids(manifest_path, cache_path, workspace_root, condition, *, seed=42, grids=1, mode="disjoint", split="val"):
    records, root, manifest_hash = _manifest(manifest_path, workspace_root)
    cache = _read_json(cache_path)
    predictions = validate_prediction_cache(cache, records, root, manifest_hash, split=split)
    plan = plan_validation_grids(records, condition, seed=seed, grids=grids, mode=mode, split=split)
    needed_label = condition.task_type.removesuffix("_present")
    eligible = [row for row in records if row["split"] == split and _truth(row, condition) is not None]
    missing = [row for row in eligible if _identity(row) not in predictions or (
        predictions[_identity(row)].presence_scores.get(needed_label) is None
        if condition.task_type in {"tree_present", "building_present", "pond_present"}
        else predictions[_identity(row)].person_count is None
    )]
    coverage = {key: value for key, value in plan.items() if key != "grids"}
    scored = []
    if not missing:
        for grid in plan["grids"]:
            pixel_predictions = [predictions[tuple(tile["identity"])] for tile in grid["tiles"]]
            selected = select_tiles(pixel_predictions, condition, cache.get("thresholds"))
            # Answers are first compared AFTER the model decisions have been made.
            exact = set(selected) == set(grid["answer_tiles"])
            scored.append({**grid, "selected_tiles": selected, "exact_set_success": exact})
    identities = [tuple(tile["identity"]) for grid in scored for tile in grid["tiles"]]
    components = [tile["component"] for grid in scored for tile in grid["tiles"]]
    occurrences = Counter(identities)
    compositions = {tuple(sorted(tuple(tile["identity"]) for tile in grid["tiles"])) for grid in scored}
    successes = sum(grid["exact_set_success"] for grid in scored)
    enough = not missing and len(scored) == grids
    return {
        "schema_version": 1, "status": "evaluated" if enough else "insufficient_data",
        "condition": {"task_type": condition.task_type, "operator": condition.operator, "n": condition.n},
        "manifest_sha256": manifest_hash, "cache_sha256": sha256_file(cache_path),
        "coverage": coverage, "missing_prediction_images": len(missing),
        "exact_set": {"successes": successes, "total": len(scored), "rate": successes / len(scored) if scored else None},
        "reuse": {"unique_images": len(occurrences), "unique_groups": len(set(components)),
                  "reused_image_occurrences": len(identities) - len(occurrences),
                  "images_used_more_than_once": sum(count > 1 for count in occurrences.values()),
                  "unique_grid_compositions": len(compositions)},
        "target_rate": TARGET_RATE, "target_achieved": None,
        "target_assessment": "not_established_by_small_validation_or_reused_grids",
        "confidence_interval": None, "independent_population_trials_claimed": False,
        "authenticity_notice": UNSIGNED_NOTICE, "new_model_inference_performed": False,
        "no_split_fallback": True, "school_or_booth_performance_measured": False,
        "grids": scored,
    }


def write_new_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
