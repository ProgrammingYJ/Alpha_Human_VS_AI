"""Read-only Commons retrieval for independently reviewed replacement candidates."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from PIL import Image

TITLES = [
    "File:Pond, Tower Hill Botanic Garden.JPG",
    "File:Shofu-en Japanese Garden Pond.jpg",
    "File:Pond with conifers and shrubs on a sunny day, Kubota Garden, Seattle.jpg",
    "File:Deep Cut Gardens Koi Pond.jpg",
    "File:Pond with small trees on rocks in scroll garden in Japanese Garden of Contemplation.jpg",
    "File:Pond and lawn in front of house in Mansfield Garden.jpg",
    "File:Garden pond in park.jpg",
    "File:Waterfall and garden.jpg",
]
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/booth/public-web-v3/extra-ponds"
OUT.mkdir(parents=True, exist_ok=True)
UA = "AlphaCaptchaEducationalBooth/1.0 (Wikimedia public-domain photo review)"

def fetch(url, maximum=2_000_000):
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=30) as response:
        data = response.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("Bounded response size exceeded")
    return data

params = {"action": "query", "format": "json", "titles": "|".join(TITLES),
          "prop": "imageinfo|revisions", "iiprop": "url|extmetadata|sha1|size",
          "iiurlwidth": 960, "rvprop": "ids|timestamp|content", "rvslots": "main"}
response = json.loads(fetch("https://commons.wikimedia.org/w/api.php?" + urlencode(params)))
pages = list(response.get("query", {}).get("pages", {}).values())

def download(page):
    if "missing" in page:
        return {"title": page["title"], "error": "missing"}
    info = page["imageinfo"][0]
    license_name = info.get("extmetadata", {}).get("LicenseShortName", {}).get("value")
    if license_name not in {"Public domain", "CC0"}:
        return {"title": page["title"], "error": "unsupported license", "license": license_name}
    data = fetch(info.get("thumburl", info["url"]))
    with Image.open(BytesIO(data)) as im:
        im.verify()
    with Image.open(BytesIO(data)) as im:
        size = list(im.size)
        im.convert("RGB").load()
    file = OUT / f"{page['pageid']}.jpg"
    file.write_bytes(data)
    return {"id": f"commons-{page['pageid']}", "title": page["title"],
            "pageid": page["pageid"], "groupId": f"commons-original-{page['pageid']}",
            "file": str(file.relative_to(ROOT)).replace("\\", "/"),
            "downloadedSha256": sha256(data).hexdigest(), "size": size,
            "info": info, "revisions": page.get("revisions", []),
            "visualReviewCompleted": False,
            "transformation": "Exact Commons full-frame thumbnail bytes; no local resizing/cropping/re-encoding"}

with ThreadPoolExecutor(max_workers=3) as pool:
    rows = list(pool.map(download, pages))
result = {"retrievedAtUtc": datetime.now(timezone.utc).isoformat(), "schoolPhotosUsed": False,
          "modelPredictionsUsedToSelectPhotos": False, "bankOrServerChanged": False,
          "searchSources": ["Commons file descriptions from explicit web search"], "images": rows}
(OUT.parent / "new-pond-provenance.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps([{k: row.get(k) for k in ("id", "title", "file", "size", "error")} for row in rows], ensure_ascii=True))
