"""Pixel-only, zero-shot tree instance counting candidate for the booth.

This is a separately pretrained Grounding DINO model, not the v1 presence
classifier and not a count model fine-tuned on school photos. No model download
is performed by inference; run scripts/fetch_tree_model.py once beforehand.
"""

from dataclasses import dataclass, asdict
import copy
import json
import math
from pathlib import Path
from collections.abc import Sequence

from PIL import Image, ImageOps


@dataclass(frozen=True)
class TreeCountProfile:
    box_threshold: float = 0.35
    text_threshold: float = 0.25
    nms_iou: float = 0.45
    shortest_edge: int = 480
    longest_edge: int = 640
    prompt: str = "a tree."

    def __post_init__(self):
        for name in ("box_threshold", "text_threshold", "nms_iou"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0,1]")
        if type(self.shortest_edge) is not int or type(self.longest_edge) is not int or not 64 <= self.shortest_edge <= self.longest_edge:
            raise ValueError("invalid tree detector image limits")
        if self.prompt != "a tree.":
            raise ValueError("the fixed public target is a tree")


class TreeCountPredictor:
    def __init__(self, model_dir=None, *, device="cpu", profile=None):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        from .dataset import sha256_file

        self.profile = profile or TreeCountProfile()
        self.device = torch.device(device)
        if self.device.type not in {"cpu", "cuda"} or self.device.type == "cuda" and not torch.cuda.is_available():
            raise ValueError("requested tree detector device is unavailable")
        self.model_dir = Path(model_dir or Path(__file__).resolve().parents[2] / "models/pretrained/grounding-dino-tiny")
        provenance = json.loads((self.model_dir / "alpha-provenance.json").read_text(encoding="utf-8"))
        if sha256_file(self.model_dir / "model.safetensors") != provenance["weights_sha256"]:
            raise ValueError("tree weights differ from pinned download provenance")
        self.processor = AutoProcessor.from_pretrained(self.model_dir, local_files_only=True, trust_remote_code=False, use_fast=False)
        self.processor.image_processor.size = {"shortest_edge": self.profile.shortest_edge, "longest_edge": self.profile.longest_edge}
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(
            self.model_dir, local_files_only=True, trust_remote_code=False, use_safetensors=True,
        ).to(self.device).eval()
        self.provenance = {**provenance, "profile": asdict(self.profile), "device": str(self.device)}
        self.last_detections = []

    def fork_for_inference(self):
        """Share eval weights, but keep preprocessing and diagnostics per worker."""
        if any(module.training for module in self.model.modules()):
            raise ValueError("shared tree model must already be in evaluation mode")
        for tensor in (*self.model.parameters(), *self.model.buffers()):
            if (tensor.device.type != self.device.type
                    or self.device.index is not None and tensor.device.index != self.device.index):
                raise ValueError("shared tree model must already be on the requested device")
        worker = copy.copy(self)
        # Grounding DINO's processor contains mutable image settings and tokenizer
        # state. Neither it nor the most recent detections belongs to the model.
        worker.processor = copy.deepcopy(self.processor)
        worker.provenance = copy.deepcopy(self.provenance)
        worker.last_detections = []
        return worker

    fork_for_worker = fork_for_inference

    def predict_counts(self, images: Sequence[Image.Image]) -> list[int]:
        import torch
        from torchvision.ops import nms

        if not images or any(not isinstance(image, Image.Image) for image in images):
            raise ValueError("tree detection accepts a non-empty sequence of PIL pixels only")
        counts, detections = [], []
        with torch.inference_mode():
            for image in images:
                rgb = ImageOps.exif_transpose(image).convert("RGB")
                inputs = self.processor(images=rgb, text=self.profile.prompt, return_tensors="pt").to(self.device)
                output = self.model(**inputs)
                result = self.processor.post_process_grounded_object_detection(
                    output, inputs.input_ids, threshold=self.profile.box_threshold,
                    text_threshold=self.profile.text_threshold, target_sizes=[(rgb.height, rgb.width)],
                )[0]
                boxes, scores = result["boxes"], result["scores"]
                if not torch.isfinite(boxes).all() or not torch.isfinite(scores).all():
                    raise RuntimeError("nonfinite tree detector output")
                valid = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
                boxes, scores = boxes[valid], scores[valid]
                keep = nms(boxes, scores, self.profile.nms_iou)
                counts.append(len(keep))
                detections.append({"tree_count": len(keep), "boxes": boxes[keep].cpu().tolist(), "scores": scores[keep].cpu().tolist()})
        self.last_detections = detections
        return counts

    def predict_at_least_three(self, images: Sequence[Image.Image]) -> list[bool]:
        return [count >= 3 for count in self.predict_counts(images)]
