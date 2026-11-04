"""Small public Kaggle file downloads. No credentials or private endpoints."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import urllib.parse
import urllib.request
import uuid


def dataset_metadata(dataset_ref: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+", dataset_ref):
        raise ValueError("dataset_ref must be owner/slug")
    request = urllib.request.Request(
        "https://www.kaggle.com/api/v1/datasets/view/" + dataset_ref,
        headers={"User-Agent": "Alpha-Captcha-AI/0.1 public-data-preparation"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.getcode() != 200 or response.headers.get("Content-Range"):
            raise ValueError("expected a complete HTTP 200 metadata response")
        if "json" not in response.headers.get("Content-Type", ""):
            raise ValueError("Kaggle metadata did not return JSON")
        metadata = json.load(response)
    if not isinstance(metadata, dict) or metadata.get("ref") != dataset_ref:
        raise ValueError("Kaggle metadata dataset ref does not match the request")
    version = metadata.get("currentVersionNumber")
    if type(version) is not int or version <= 0:
        raise ValueError("Kaggle dataset version must be a positive integer")
    return metadata


def fetch_kaggle_file(
    dataset_ref: str, remote_path: str, destination: Path,
    *, workspace_root: Path, max_bytes: int, expected_kind: str,
) -> dict:
    """Download into raw/kaggle only, bounded and atomic; never unpack archives."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+", dataset_ref):
        raise ValueError("dataset_ref must be owner/slug")
    remote = PurePosixPath(remote_path)
    if remote.is_absolute() or ".." in remote.parts or "\\" in remote_path:
        raise ValueError("invalid remote path")
    destination = Path(destination).resolve()
    # Do not resolve the allowed prefix: the Kaggle root may itself be a link
    # into school data or outside this workspace.
    allowed = Path(workspace_root).resolve() / "data/raw/kaggle"
    if not destination.is_relative_to(allowed):
        raise ValueError("downloads must remain in data/raw/kaggle")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if expected_kind not in {"json", "image"}:
        raise ValueError("expected_kind must be json or image")
    endpoint = "download-raw" if expected_kind == "json" else "download"
    url = (
        "https://www.kaggle.com/api/v1/datasets/" + endpoint + "/" + dataset_ref + "/"
        + urllib.parse.quote(remote_path, safe="")
    )

    def file_info(path: Path) -> dict:
        size = path.stat().st_size
        if size <= 0 or size > max_bytes:
            raise ValueError("existing/downloaded file has invalid size")
        if expected_kind == "json":
            with path.open(encoding="utf-8-sig") as source:
                value = json.load(source)
            if not isinstance(value, (dict, list)):
                raise ValueError("expected a JSON object or array")
        else:
            from PIL import Image
            with Image.open(path) as picture:
                picture.verify()
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        return {"url": url, "remote_path": remote_path, "bytes": size, "sha256": digest}

    if destination.exists():
        return {**file_info(destination), "downloaded": False}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Alpha-Captcha-AI/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("xb") as output:
            if response.getcode() != 200 or response.headers.get("Content-Range"):
                raise ValueError("expected a complete HTTP 200 file response")
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise ValueError("remote file exceeds max_bytes")
            kind = response.headers.get("Content-Type", "").lower()
            if expected_kind == "json" and "json" not in kind:
                raise ValueError("remote endpoint did not return JSON; not saving HTML/ZIP")
            if expected_kind == "image" and not kind.startswith("image/"):
                raise ValueError("remote endpoint did not return an image")
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("stream exceeds max_bytes")
                output.write(chunk)
            if length and size != int(length):
                raise ValueError("incomplete download")
        result = file_info(temporary)
        if destination.exists():
            raise FileExistsError(destination)
        temporary.rename(destination)
        return {**result, "downloaded": True}
    finally:
        if temporary.exists():
            temporary.unlink()
