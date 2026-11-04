"""Copy reviewed Kaggle photos into a PRIVATE local integration demo bank.

No downloads, fitting, school access or public deployment. Existing v1 train,
val and test examples are deliberately reused for integration, never accuracy.
"""

import argparse
import json
from pathlib import Path
import uuid

from PIL import Image

from alpha_captcha.dataset import load_jsonl, sha256_file, validate_manifest


# Positives are identified by reviewed labels, not by model predictions.
# Tree >=3 was additionally checked from the actual RGB on 2026-10-26.
PRESENCE_GROUPS = {
    "tree_ge3": {"positive": [9, 10, 16, 19], "negative": [2, 15, 17, 50, 54, 55]},
    "building": {"positive": [12, 50, 54, 55], "negative": [2, 46, 15, 17, 9, 10, 49]},
    "pond": {"positive": [24, 28, 58, 59], "negative": [2, 15, 36, 37, 45, 49, 46]},
}
PERSON_GROUPS = {
    "person_ge3": {
        "positive": ["482800", "523033", "140556", "445834"],
        "negative": ["128658", "270386", "550084", "104455", "551439", "526728", "505942"],
    },
    "person_present": {
        "positive": ["482800", "523033", "140556", "445834"],
        "negative": ["128658", "270386", "550084", "104455", "481257", "186265", "67680"],
    },
}
TREE_REASONS = {
    9: "Orchard: at least three separate real tree trunks/canopies are clearly distinguishable; exact total uncertain.",
    10: "Forest entrance: at least three separate real tree trunks are clearly visible; exact total uncertain.",
    16: "Pasture: at least three distinct real trees are visible behind the fences; exact total uncertain.",
    19: "Path: multiple separate cypress trees on both sides, clearly at least three; exact total uncertain.",
    2: "Ship deck and pools: no visible real trees.",
    15: "Open sea and rocks: no visible real trees.",
    17: "Bullring close view: no visible real trees.",
    50: "Bathroom: small potted plant is excluded from the real tree definition.",
    54: "Bathroom: no visible real trees.",
    55: "Empty room: no visible real trees in the photograph.",
}


def prepare(root, destination):
    root = Path(root).resolve()
    destination = Path(destination).resolve()
    allowed = root / "data" / "booth"
    if not destination.is_relative_to(allowed):
        raise ValueError("demo bank must remain inside data/booth, never web/public")
    presence_path = root / "data/manifests/presence-ml-v1.jsonl"
    person_path = root / "data/manifests/coco-person-reviewed-split.jsonl"
    presence, person = load_jsonl(presence_path), load_jsonl(person_path)
    validate_manifest(presence, root, require_split=True)
    validate_manifest(person, root, require_split=True)
    person_by_id = {row["image_id"]: row for row in person}
    if (destination / "demo-bank.json").exists() or (destination / "demo-images").exists():
        raise FileExistsError("existing demo banks/images are never overwritten")
    selected = {}
    topics = {}

    def add(row):
        key = (row["dataset_ref"], row["image_id"])
        selected.setdefault(key, {"row": row, "tree_count": None, "tree_at_least3": None,
                                  "tree_minimum": None, "tree_review": None})
        return key

    for topic, classes in PRESENCE_GROUPS.items():
        topics[topic] = {"positive": [], "negative": []}
        for category, indices in classes.items():
            for index in indices:
                row = presence[index]
                if topic in {"building", "pond"} and row["labels"][topic] is not (category == "positive"):
                    raise ValueError(f"frozen reviewed label no longer matches {topic} candidate {index}")
                key = add(row)
                topics[topic][category].append(key)
                if topic == "tree_ge3":
                    selected[key].update(tree_at_least3=category == "positive",
                                         tree_count=0 if category == "negative" else None,
                                         tree_minimum=3 if category == "positive" else 0,
                                         tree_review=TREE_REASONS[index])
    for topic, classes in PERSON_GROUPS.items():
        topics[topic] = {"positive": [], "negative": []}
        for category, image_ids in classes.items():
            for image_id in image_ids:
                row = person_by_id[image_id]
                count = row["person"]["count"]
                if row["person"]["count_status"] != "verified" or count is None:
                    raise ValueError("demo people require the existing verified visual review")
                if (count >= (3 if topic == "person_ge3" else 1)) is not (category == "positive"):
                    raise ValueError("person demo category no longer matches the reviewed count")
                topics[topic][category].append(add(row))
    destination.mkdir(parents=True, exist_ok=True)
    image_dir = destination / "demo-images"
    image_dir.mkdir()
    images, key_ids = [], {}
    for key, item in selected.items():
        row = item["row"]
        opaque = "demo-" + uuid.uuid5(uuid.NAMESPACE_URL,
                                      f"{key[0]}:{key[1]}:{row['sha256']}").hex
        key_ids[key] = opaque
        source = root / row["image_path"]
        image_path = image_dir / f"{opaque}.jpg"
        if not source.resolve().is_relative_to(root / "data/raw/kaggle"):
            raise ValueError("only the validated Kaggle root may supply demo pixels")
        with Image.open(source) as image:
            if image.format != "JPEG":
                raise ValueError("demo copying preserves original JPEG bytes")
        with image_path.open("xb") as stream:
            stream.write(source.read_bytes())
        if sha256_file(image_path) != row["sha256"]:
            raise RuntimeError("copied demo bytes differ from the original")
        count = row["person"]["count"] if row["person"]["count_status"] == "verified" else None
        labels = {"personCount": count, "treeCount": item["tree_count"],
                  "treeAtLeast3": item["tree_at_least3"],
                  "building": row["labels"]["building"], "pond": row["labels"]["pond"]}
        if item["tree_minimum"] is not None:
            labels["treeCountMinimum"] = item["tree_minimum"]
        images.append({"id": opaque, "file": image_path.relative_to(destination).as_posix(),
                       "source": "kaggle", "groupId": row["group_id"], "labels": labels,
                       "usageNote": row["usage_note"] + " Local integration demo only; no blanket public redistribution clearance.",
                       "provenance": {"datasetRef": row["dataset_ref"], "datasetVersion": row["dataset_version"],
                                      "imageId": row["image_id"], "sha256": row["sha256"],
                                      "originalDevelopmentSplit": row["split"]},
                       "labelReview": {"existingReview": row.get("label_review", row.get("person_review")),
                                       "treeAtLeast3Reviewer": "Codex" if item["tree_review"] else None,
                                       "treeAtLeast3ReviewDate": "2026-10-26" if item["tree_review"] else None,
                                       "treeAtLeast3Reason": item["tree_review"]}})
    topic_ids = {topic: {category: [key_ids[key] for key in keys] for category, keys in classes.items()}
                 for topic, classes in topics.items()}
    bank = {"schemaVersion": 1, "demoOnly": True, "schoolPhotosUsed": False,
            "purpose": "Local website/ML/click integration, not new model accuracy or 40-percent calibration.",
            "sourceManifestSha256": {str(presence_path.relative_to(root)): sha256_file(presence_path),
                                     str(person_path.relative_to(root)): sha256_file(person_path)},
            "images": images, "topicCandidates": topic_ids}
    bank_path = destination / "demo-bank.json"
    with bank_path.open("x", encoding="utf-8") as stream:
        json.dump(bank, stream, ensure_ascii=False, indent=2)
    report = {"images": len(images), "bytes": sum((destination / image["file"]).stat().st_size for image in images),
              "bank": str(bank_path), "localOnly": True, "publicDeploymentCleared": False,
              "topicCounts": {topic: {category: len(ids) for category, ids in classes.items()}
                              for topic, classes in topic_ids.items()},
              "treeExactCountNotInvented": True, "newModelInferencePerformed": False}
    with (destination / "demo-preparation-report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.destination or args.root / "data/booth"), indent=2))


if __name__ == "__main__":
    main()
