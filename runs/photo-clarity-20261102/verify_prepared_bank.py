"""Read-only local bank QA; no model, administrator capability or network use."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from PIL import Image


def difference_hash(image: Image.Image) -> int:
    values = list(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).getdata())
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | int(values[y * 9 + x] > values[y * 9 + x + 1])
    return bits


def audit(root: Path) -> dict:
    base = root / "data/booth/public-web-v3"
    raw = (base / "bank.json").read_bytes()
    bank = json.loads(raw)
    assert bank["publicDeploymentCleared"] is True and bank["schoolPhotosUsed"] is False
    assert bank["modelPredictionsUsedToSelectPhotos"] is False
    old = []
    for version in ("public-web-v1", "public-web-v2"):
        old.extend(json.loads((base.parent / version / "bank.json").read_text(encoding="utf-8"))["images"])
    old_by_hash = {photo["provenance"]["sha256"]: photo for photo in old}
    photos = bank["images"]
    hashes, ids, groups, originals, original_hashes = set(), set(), set(), set(), set()
    checked, label_differences, visual_hashes = [], [], []
    retained = 0
    for photo in photos:
        path = (base / photo["file"]).resolve()
        assert path.is_relative_to(base.resolve()), "Image escaped bank root"
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        provenance = photo["provenance"]
        assert actual == provenance["sha256"]
        assert actual not in hashes and photo["id"] not in ids and photo["groupId"] not in groups
        hashes.add(actual); ids.add(photo["id"]); groups.add(photo["groupId"])
        assert provenance["license"] in {"CC0", "CC0 1.0", "Public domain"}
        assert provenance["sourceUrl"].startswith("https://")
        for field, seen in (("originalId", originals), ("originalSha1", original_hashes)):
            value = provenance.get(field)
            if value:
                assert value not in seen, f"Repeated {field}"
                seen.add(value)
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            assert image.mode == "RGB" and min(image.size) >= 128
            assert not image.getexif(), "Transmitted fixture should have no EXIF"
            checked.append({"id": photo["id"], "sha256": actual, "bytes": len(data), "size": list(image.size)})
            visual_hashes.append((photo["id"], difference_hash(image)))
        previous = old_by_hash.get(actual)
        if previous:
            retained += 1
            assert previous["groupId"] == photo["groupId"]
            fields = ("personCount", "treeCount", "treeAtLeast3", "treeCountMinimum", "building", "pond")
            differences = [field for field in fields if previous["labels"].get(field) != photo["labels"].get(field)]
            if differences:
                label_differences.append({"id": photo["id"], "fields": differences})
    assert not label_differences, "Retained photo labels differ from immutable old registrations"
    assert retained == bank["retainedCount"] and len(photos) - retained == bank["newCount"]
    assert len(old) - retained == bank["retiredCount"]
    near = []
    for i, first in enumerate(visual_hashes):
        for second in visual_hashes[i + 1:]:
            distance = (first[1] ^ second[1]).bit_count()
            if distance <= 4:
                near.append({"first": first[0], "second": second[0], "dHashHamming": distance})
    return {"schema": 1, "passed": True, "sourceBankSha256": hashlib.sha256(raw).hexdigest(),
            "photoCount": len(photos), "retained": retained, "retired": bank["retiredCount"], "new": len(photos) - retained,
            "totalBytes": sum(row["bytes"] for row in checked), "photos": checked,
            "checks": {"allPixelHashesMatch": True, "fullDecodeRgbAndMin128": True, "noExif": True,
                       "noDuplicateIdsHashesDeclaredGroupsOriginalIdsOrSha1": True, "retainedLabelsAndGroupsUnchanged": True},
            "nearDuplicateFlags": near, "networkOrAdministratorOrModelAccess": False,
            "limitations": ["Prepared local bank only; not proof of production active state or model accuracy", "dHash<=4 is a heuristic; unknown capture relations and independent human labels remain unproven"]}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    output = Path(sys.argv[1])
    assert not output.exists(), "Preserve existing audit report"
    report = audit(root)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in ("passed", "photoCount", "retained", "retired", "new", "totalBytes", "nearDuplicateFlags")}, ensure_ascii=False))
