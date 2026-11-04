"""Upload the private Kaggle demo bank to a LOCAL preview admin API only.

The operator key is read from stdin, never arguments, reports or logs. Demo
photos have not received blanket public redistribution clearance.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, default=Path("data/booth/demo-bank.json"))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--execute", action="store_true", help="upload to the controlled local preview")
    parser.add_argument("--admin-key-stdin", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    if (parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        parser.error("Kaggle demo uploading is restricted to a local preview, never the deployed site")
    if args.output.exists():
        parser.error("report output already exists")
    if args.execute and not args.admin_key_stdin:
        parser.error("execution requires --admin-key-stdin; keys must not appear in command arguments")
    bank_path = args.bank.resolve()
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    if bank.get("demoOnly") is not True or bank.get("schoolPhotosUsed") is not False:
        parser.error("this importer accepts only the explicitly private Kaggle demo bank")
    prepared = []
    for image in bank["images"]:
        path = (bank_path.parent / image["file"]).resolve()
        if not path.is_relative_to(bank_path.parent) or image.get("source") != "kaggle":
            parser.error("demo photo escaped its private bank or has an unsupported source")
        data = path.read_bytes()
        if len(data) > 20_000_000 or hashlib.sha256(data).hexdigest() != image["provenance"]["sha256"]:
            parser.error("demo photo hash/size validation failed")
        metadata = {**image["labels"], "groupId": image["groupId"], "source": "kaggle",
                    "usageNote": image["usageNote"] + " Provenance: " + json.dumps(image["provenance"], separators=(",", ":"))}
        prepared.append((image["id"], path.name, data, metadata))
    key = None
    if args.execute:
        key = sys.stdin.readline(4097).strip()
        if not key or len(key) > 4096:
            parser.error("stdin did not contain a bounded non-empty admin key")
    uploaded = []
    for image_id, filename, data, metadata in prepared:
        if not args.execute:
            continue
        boundary = "alpha" + uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"metadata\"\r\n"
                "Content-Type: application/json; charset=utf-8\r\n\r\n").encode()
        body += json.dumps(metadata, ensure_ascii=False).encode("utf-8")
        body += (f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
                 "Content-Type: image/jpeg\r\n\r\n").encode()
        body += data + f"\r\n--{boundary}--\r\n".encode()
        request = Request(args.base_url.rstrip("/") + "/api/admin/photos", data=body,
                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "x-admin-key": key})
        with urlopen(request, timeout=20) as response:
            if response.status not in {200, 201}:
                raise RuntimeError(f"local photo upload returned HTTP {response.status}")
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("local upload response is too large")
        result = json.loads(raw)
        uploaded.append({"demoId": image_id, "serverPhotoId": result.get("id", result.get("photo", {}).get("id"))})
    report = {"mode": "execute" if args.execute else "dry-run", "origin": parsed.netloc,
              "verifiedImages": len(prepared), "uploadedImages": len(uploaded), "uploads": uploaded,
              "adminKeyStoredOrLogged": False, "publicDeploymentCleared": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({name: report[name] for name in ("mode", "verifiedImages", "uploadedImages", "adminKeyStoredOrLogged")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
