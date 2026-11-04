"""Validate and optionally upload explicitly cleared public booth photos.

Unlike import_booth_demo.py, this accepts only a separate public-domain/CC0
question bank. It never turns school/Kaggle development data into public assets.
Administrator credentials enter through stdin only and are not persisted.
"""

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid

from PIL import Image


PUBLIC_HOSTS = {"human.marulee.dev", "bot.marulee.dev"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
ALLOWED_LICENSES = {"Public domain", "CC0"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
USER_AGENT = "AlphaCaptchaPublicBankImporter/1.0"


def controlled_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or parsed.hostname not in PUBLIC_HOSTS | LOCAL_HOSTS
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise ValueError("public import requires a controlled booth origin")
    if parsed.hostname in PUBLIC_HOSTS and (parsed.scheme != "https" or parsed.port not in {None, 443}):
        raise ValueError("deployed booth imports require HTTPS on its standard port")
    return f"{parsed.scheme}://{parsed.netloc}"


def _text(value, name, maximum):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f"invalid {name}")
    return value.strip()


def validated_labels(value):
    if not isinstance(value, dict):
        raise ValueError("photo labels must be an object")
    labels = {}
    for name in ("personCount", "treeCount", "treeCountMinimum"):
        count = value.get(name)
        if count is not None and (type(count) is not int or not 0 <= count <= 10000):
            raise ValueError(f"invalid {name}")
        labels[name] = count
    for name in ("treeAtLeast3", "building", "pond"):
        flag = value.get(name)
        if flag is not None and type(flag) is not bool:
            raise ValueError(f"invalid {name}")
        labels[name] = flag
    exact, minimum, flag = labels["treeCount"], labels["treeCountMinimum"], labels["treeAtLeast3"]
    if exact is not None and minimum is not None and exact < minimum:
        raise ValueError("tree count is smaller than the documented minimum")
    if exact is not None and flag is not None and flag != (exact >= 3):
        raise ValueError("tree count and tree-at-least-three disagree")
    if minimum is not None and minimum >= 3 and flag is False:
        raise ValueError("tree minimum and tree-at-least-three disagree")
    return labels


def prepare_bank(bank_path):
    bank_path = Path(bank_path).resolve()
    bank = json.loads(bank_path.read_text(encoding="utf-8-sig"))
    if (not isinstance(bank, dict) or bank.get("publicDeploymentCleared") is not True
            or bank.get("schoolPhotosUsed") is not False or bank.get("demoOnly") is True):
        raise ValueError("only an explicitly cleared non-school public photo bank is accepted")
    images = bank.get("images")
    if not isinstance(images, list) or not 1 <= len(images) <= 128:
        raise ValueError("the reviewed public bank must contain 1..128 photos")
    prepared, identities, hashes = [], set(), set()
    for row in images:
        if not isinstance(row, dict) or row.get("source") != "other":
            raise ValueError("public test photos must have an explicit other source, never school/Kaggle")
        image_id = _text(row.get("id"), "photo ID", 200)
        group = _text(row.get("groupId"), "original group", 200)
        file = _text(row.get("file"), "photo path", 1000)
        path = (bank_path.parent / file).resolve()
        if not path.is_relative_to(bank_path.parent) or not path.is_file():
            raise ValueError("public photo escaped its bank or is missing")
        if image_id in identities:
            raise ValueError("public fixture bank repeats a photo identity")
        provenance = row.get("provenance")
        if not isinstance(provenance, dict) or provenance.get("license") not in ALLOWED_LICENSES:
            raise ValueError("public test photos require documented Public domain or CC0 clearance")
        source = urlsplit(_text(provenance.get("sourceUrl"), "public source URL", 1500))
        if source.scheme != "https" or not source.hostname or source.username or source.password:
            raise ValueError("photo provenance must include a public HTTPS source URL")
        expected_hash = provenance.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("photo provenance needs its downloaded SHA-256")
        size = path.stat().st_size
        if not 0 < size <= MAX_IMAGE_BYTES:
            raise ValueError("public photo exceeds the server's 8MiB bound or is empty")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_hash or expected_hash in hashes:
            raise ValueError("public photo hash mismatch or repeated image bytes")
        with Image.open(BytesIO(data)) as image:
            format = image.format
            image.verify()
        if format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("public upload supports JPEG, PNG and WebP only")
        with Image.open(BytesIO(data)) as image:
            image.load()
        labels = validated_labels(row.get("labels"))
        note = _text(row.get("usageNote"), "usage note", 2000)
        # Retain bounded provenance as SERVER-ONLY metadata. Never encode any
        # source title/labels into the uploaded filename or public tile ID.
        encoded = json.dumps(provenance, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > 4000:
            raise ValueError("photo provenance exceeds the server metadata bound")
        metadata = {**labels, "groupId": group, "source": "other", "usageNote": note,
                    "provenance": provenance}
        if len(json.dumps(metadata, ensure_ascii=False)) > 8192:
            raise ValueError("public photo metadata exceeds the server request bound")
        mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[format]
        extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[format]
        prepared.append({"id": image_id, "data": data, "mime": mime,
                         "filename": f"{uuid.uuid4().hex}.{extension}", "metadata": metadata})
        identities.add(image_id)
        hashes.add(expected_hash)
    return prepared


class NoRedirect(HTTPRedirectHandler):
    """Never forward an administrator capability to a redirect destination."""
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def multipart(photo):
    boundary = "alpha" + uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"metadata\"\r\n"
            "Content-Type: application/json; charset=utf-8\r\n\r\n").encode()
    body += json.dumps(photo["metadata"], ensure_ascii=False).encode("utf-8")
    body += (f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
             f"filename=\"{photo['filename']}\"\r\nContent-Type: {photo['mime']}\r\n\r\n").encode()
    return boundary, body + photo["data"] + f"\r\n--{boundary}--\r\n".encode()


def upload_one(origin, key, photo, opener):
    boundary, body = multipart(photo)
    request = Request(origin + "/api/admin/photos", data=body, headers={
        "Accept": "application/json", "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": USER_AGENT, "x-admin-key": key,
    })
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 201:
                raise ValueError("public upload returned an unexpected successful status")
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("public upload response is too large")
        json.loads(raw)
        return "uploaded"
    except HTTPError as error:
        if error.code == 409:
            raw = error.read(65537)
            if len(raw) <= 65536:
                try:
                    if json.loads(raw).get("code") == "duplicate_photo":
                        return "already_present"
                except (ValueError, AttributeError):
                    pass
        # Do not print request/response bodies, administrator headers or secrets.
        raise ValueError(f"public upload was rejected (HTTP {error.code})") from None


def save_report(path, report):
    temporary = path.with_name(path.name + ".pending")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, default=Path("data/booth/public-web-v1/bank.json"))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--admin-key-stdin", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        origin = controlled_origin(args.base_url)
        if args.output.exists() or args.output.with_name(args.output.name + ".pending").exists():
            raise ValueError("choose a new report path; existing reports are preserved")
        if args.execute and not args.admin_key_stdin:
            raise ValueError("--execute requires --admin-key-stdin; never pass a key in arguments")
        photos = prepare_bank(args.bank)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    key = None
    if args.execute:
        key = sys.stdin.readline(4097).strip()
        if not key or len(key) > 4096 or any(ord(char) < 33 or ord(char) == 127 for char in key):
            parser.error("stdin did not contain a bounded administrator key")
    report = {"mode": "execute" if args.execute else "dry-run", "origin": origin,
              "verifiedImages": len(photos), "uploadedImages": 0, "alreadyPresentImages": 0,
              "completed": False, "publicDeploymentCleared": True, "schoolPhotosUsed": False,
              "administratorKeyStoredOrLogged": False, "results": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_report(args.output, report)
    opener = build_opener(NoRedirect())
    if args.execute:
        for photo in photos:
            try:
                status = upload_one(origin, key, photo, opener)
            except Exception as error:
                # A checkpoint preserves completed rows; reruns use a NEW
                # report and safely skip the server's duplicate-photo response.
                report["failedPhotoId"] = photo["id"]
                report["failureType"] = type(error).__name__
                save_report(args.output, report)
                print(json.dumps({"completed": False, "uploadedImages": report["uploadedImages"],
                                  "alreadyPresentImages": report["alreadyPresentImages"],
                                  "failureType": type(error).__name__}))
                return 1
            report["results"].append({"publicPhotoId": photo["id"], "status": status})
            report["uploadedImages" if status == "uploaded" else "alreadyPresentImages"] += 1
            save_report(args.output, report)
    report["completed"] = True
    save_report(args.output, report)
    print(json.dumps({name: report[name] for name in ("mode", "verifiedImages", "uploadedImages",
                     "alreadyPresentImages", "completed", "administratorKeyStoredOrLogged")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
