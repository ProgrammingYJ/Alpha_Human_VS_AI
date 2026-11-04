"""Export/apply explicit Kaggle label reviews. Blank always means unknown."""

import argparse
import csv
from copy import deepcopy
from pathlib import Path

from alpha_captcha.dataset import load_jsonl, save_jsonl, validate_manifest


KEYS = ["dataset_ref", "image_id", "sha256", "image_path", "tree", "building", "pond",
        "person_present", "person_count", "reviewer", "review_note"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "apply"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    records = load_jsonl(args.manifest)
    validate_manifest(records, args.root)
    if args.action == "export":
        args.reviews.parent.mkdir(parents=True, exist_ok=True)
        with args.reviews.open("x", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=KEYS)
            writer.writeheader()
            for record in records:
                writer.writerow({key: record[key] for key in KEYS[:4]})
        print(f"Exported {len(records)} review rows. Blank labels are unknown; no labels inferred.")
        return 0
    if args.output is None:
        parser.error("apply requires --output (new JSONL path)")
    result = deepcopy(records)
    indexed = {(row["dataset_ref"], row["image_id"]): row for row in result}
    if len(indexed) != len(result):
        raise ValueError("review requires unique dataset_ref/image_id; separate source versions")
    seen = set()
    applied = 0

    def boolean(value: str) -> bool | None:
        if value == "":
            return None
        if value not in {"0", "1"}:
            raise ValueError("review flags must be 0, 1 or blank")
        return value == "1"

    with args.reviews.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != KEYS:
            raise ValueError("unexpected review CSV header")
        for review in reader:
            key = (review["dataset_ref"], review["image_id"])
            if key not in indexed or key in seen:
                raise ValueError("unknown or duplicate review identity")
            seen.add(key)
            record = indexed[key]
            if review["sha256"] != record["sha256"] or review["image_path"] != record["image_path"]:
                raise ValueError("review identity/hash/path does not match manifest")
            flags = {label: boolean(review[label].strip()) for label in ("tree", "building", "pond")}
            presence = boolean(review["person_present"].strip())
            count_text = review["person_count"].strip()
            if count_text and (not count_text.isascii() or not count_text.isdecimal()):
                raise ValueError("review person_count must be a nonnegative integer or blank")
            count = int(count_text) if count_text else None
            if not any(value is not None for value in flags.values()) and presence is None and count is None:
                continue
            if not review["reviewer"].strip() or not review["review_note"].strip():
                raise ValueError("annotated rows require reviewer and review_note")
            for label, flag in flags.items():
                if flag is not None:
                    record["labels"][label] = flag
            person = record["person"]
            if count is not None:
                if person["iscrowd"]:
                    raise ValueError("crowd exact counts cannot be approved by this review tool")
                if presence is not None and presence != (count >= 1):
                    raise ValueError("person presence and exact count disagree")
                # A count review does not certify the coordinates of original boxes.
                record.setdefault("annotation_boxes", person["boxes"])
                person.update(count=count, count_status="verified", present=count >= 1, boxes=None)
            elif presence is not None:
                person["present"] = presence
            record["label_review"] = {"reviewer": review["reviewer"].strip(), "note": review["review_note"].strip()}
            applied += 1
    validate_manifest(result, args.root)
    save_jsonl(result, args.output)
    print(f"Applied {applied} reviewed rows. Original manifest and images were preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
