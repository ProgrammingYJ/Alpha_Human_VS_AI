"""Fetch pinned public Grounding DINO weights; no school data or fitting."""

import json
from pathlib import Path

from huggingface_hub import snapshot_download
from alpha_captcha.dataset import sha256_file


MODEL_ID = "IDEA-Research/grounding-dino-tiny"
REVISION = "a2bb814dd30d776dcf7e30523b00659f4f141c71"


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    destination = root / "models/pretrained/grounding-dino-tiny"
    snapshot_download(
        repo_id=MODEL_ID, revision=REVISION, local_dir=destination,
        allow_patterns=["*.json", "vocab.txt", "model.safetensors"],
    )
    weights = destination / "model.safetensors"
    report = {
        "model_id": MODEL_ID, "revision": REVISION, "license": "Apache-2.0",
        "source": "https://huggingface.co/" + MODEL_ID,
        "weights_sha256": sha256_file(weights), "weights_bytes": weights.stat().st_size,
        "trained_in_this_project": False, "school_data_used": False,
        "purpose": "Optional zero-shot tree instance detector; not a calibrated 40% model or Pi benchmark.",
    }
    (destination / "alpha-provenance.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
