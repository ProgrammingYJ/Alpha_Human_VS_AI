"""Limited SSDLite transfer learning for real person instances and counts."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision.models.detection import (
    SSDLite320_MobileNet_V3_Large_Weights, ssdlite320_mobilenet_v3_large,
)

from .dataset import load_jsonl, sha256_file, validate_manifest


@dataclass(frozen=True)
class PersonTrainingProfile:
    epochs: int = 1
    batch_size: int = 2
    max_training_images: int = 32
    seed: int = 42
    learning_rate: float = 0.0001
    weight_decay: float = 0.0001
    input_size: int = 320
    score_threshold: float = 0.5
    nms_iou_threshold: float = 0.45
    minimum_original_box_height: float = 8.0
    minimum_original_box_area: float = 64.0

    def __post_init__(self):
        for name in ("epochs", "batch_size", "max_training_images", "input_size", "seed"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer")
        if min(self.epochs, self.batch_size, self.max_training_images, self.input_size) <= 0:
            raise ValueError("training limits and input size must be positive")
        if self.input_size != 320:
            raise ValueError("this SSDLite architecture uses a fixed input of 320")
        for name in ("learning_rate", "weight_decay", "score_threshold", "nms_iou_threshold",
                     "minimum_original_box_height", "minimum_original_box_area"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.learning_rate <= 0 or self.weight_decay < 0:
            raise ValueError("invalid optimizer parameters")
        if not 0 <= self.score_threshold <= 1 or not 0 < self.nms_iou_threshold <= 1:
            raise ValueError("invalid detection thresholds")
        if self.minimum_original_box_height < 0 or self.minimum_original_box_area < 0:
            raise ValueError("minimum size cannot be negative")


def letterbox_person(image: Image.Image, boxes=None, size: int = 320):
    """Keep the complete RGB image; transform xyxy boxes without a center crop."""
    image = image.convert("RGB")
    width, height = image.size
    scale = min(size / width, size / height)
    resized_width, resized_height = max(1, round(width * scale)), max(1, round(height * scale))
    left, top = (size - resized_width) // 2, (size - resized_height) // 2
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    canvas.paste(image.resize((resized_width, resized_height), Image.Resampling.BILINEAR), (left, top))
    tensor = torch.from_numpy(np.array(canvas, dtype=np.float32).transpose(2, 0, 1).copy()) / 255.0
    geometry = {"width": width, "height": height, "scale_x": resized_width / width,
                "scale_y": resized_height / height, "left": left, "top": top}
    transformed = None
    if boxes is not None:
        transformed = torch.as_tensor(boxes, dtype=torch.float32).reshape(-1, 4).clone()
        transformed[:, (0, 2)] = transformed[:, (0, 2)] * geometry["scale_x"] + left
        transformed[:, (1, 3)] = transformed[:, (1, 3)] * geometry["scale_y"] + top
    return tensor, transformed, geometry


def decode_person_output(output: dict, geometry: dict, profile: PersonTrainingProfile) -> dict:
    """Model already performs NMS; filter class 1 and size in original pixels."""
    boxes = output["boxes"].detach().cpu().clone()
    scores = output["scores"].detach().cpu()
    labels = output["labels"].detach().cpu()
    if boxes.ndim != 2 or boxes.shape[1:] != (4,) or len(boxes) != len(scores) or len(boxes) != len(labels):
        raise ValueError("invalid detector outputs")
    if not torch.isfinite(boxes).all() or not torch.isfinite(scores).all():
        raise ValueError("nonfinite detector outputs")
    boxes[:, (0, 2)] = ((boxes[:, (0, 2)] - geometry["left"]) / geometry["scale_x"]).clamp(0, geometry["width"])
    boxes[:, (1, 3)] = ((boxes[:, (1, 3)] - geometry["top"]) / geometry["scale_y"]).clamp(0, geometry["height"])
    width, height = boxes[:, 2] - boxes[:, 0], boxes[:, 3] - boxes[:, 1]
    keep = ((labels == 1) & (scores >= profile.score_threshold) & (width > 0)
            & (height >= profile.minimum_original_box_height)
            & (width * height >= profile.minimum_original_box_area))
    return {"person_count": int(keep.sum().item()), "boxes": boxes[keep].tolist(), "scores": scores[keep].tolist()}


class PersonDataset(Dataset):
    def __init__(self, rows: list[dict], root: Path, profile: PersonTrainingProfile):
        self.rows, self.root, self.profile = rows, Path(root).resolve(), profile

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        person = row["person"]
        if (person["count_status"] != "verified" or person["iscrowd"] or person["boxes"] is None
                or row.get("person_review", {}).get("detection_eligible") is not True):
            raise ValueError("detector fitting requires reviewed complete individual boxes")
        validate_manifest([row], self.root, verify_files=True)
        with Image.open(self.root / row["image_path"]) as image:
            tensor, boxes, _ = letterbox_person(image, person["boxes"], self.profile.input_size)
        return tensor, {"boxes": boxes, "labels": torch.ones(len(boxes), dtype=torch.int64)}


def parameter_digest(module: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(module.state_dict().items()):
        digest.update(name.encode())
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def build_person_model(profile: PersonTrainingProfile, *, pretrained=True):
    model = ssdlite320_mobilenet_v3_large(
        weights=SSDLite320_MobileNet_V3_Large_Weights.COCO_V1 if pretrained else None,
        weights_backbone=None, score_thresh=profile.score_threshold,
        nms_thresh=profile.nms_iou_threshold, detections_per_img=100,
    )
    for parameter in model.backbone.parameters():
        parameter.requires_grad_(False)
    return model


def set_person_training_mode(model):
    model.train()
    model.backbone.eval()
    # Small batches and 1x1 features: freeze running statistics in all BN layers.
    for module in model.modules():
        if isinstance(module, nn.modules.batchnorm._BatchNorm):
            module.eval()


def predict_person(model, images: list[Image.Image], profile: PersonTrainingProfile, *, device=None, prepare_model=True):
    device = torch.device(device or next(model.parameters()).device)
    if prepare_model:
        model.eval()
    elif any(module.training for module in model.modules()):
        raise ValueError("shared person model must already be in evaluation mode")
    inputs, geometries = [], []
    for image in images:
        tensor, _, geometry = letterbox_person(image, size=profile.input_size)
        inputs.append(tensor.to(device))
        geometries.append(geometry)
    if not inputs:
        return []
    with torch.inference_mode():
        outputs = model(inputs)
    return [decode_person_output(output, geometry, profile) for output, geometry in zip(outputs, geometries)]


def evaluate_person(model, rows, root, profile, *, device):
    predictions, absolute_errors = [], []
    thresholds = {str(n): {"correct": 0, "total": 0} for n in range(2, 6)}
    exact, presence_correct = 0, 0
    confusion = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    started = time.perf_counter()
    for row in rows:
        with Image.open(root / row["image_path"]) as image:
            result = predict_person(model, [image], profile, device=device)[0]
        actual, predicted = row["person"]["count"], result["person_count"]
        absolute_errors.append(abs(actual - predicted))
        exact += actual == predicted
        presence_correct += (actual >= 1) == (predicted >= 1)
        confusion["tp" if actual >= 1 and predicted >= 1 else "fp" if predicted >= 1 else "fn" if actual >= 1 else "tn"] += 1
        for n in range(2, 6):
            thresholds[str(n)]["correct"] += (actual >= n) == (predicted >= n)
            thresholds[str(n)]["total"] += 1
        predictions.append({"image_id": row["image_id"], "sha256": row["sha256"],
                            "actual_count": actual, **result})
    denominator = len(rows)
    precision_denominator = confusion["tp"] + confusion["fp"]
    recall_denominator = confusion["tp"] + confusion["fn"]
    precision = confusion["tp"] / precision_denominator if precision_denominator else None
    recall = confusion["tp"] / recall_denominator if recall_denominator else None
    f1 = 2 * confusion["tp"] / (2 * confusion["tp"] + confusion["fp"] + confusion["fn"]) if (2 * confusion["tp"] + confusion["fp"] + confusion["fn"]) else None
    return {"images": denominator, "exact_count_accuracy": exact / denominator if denominator else None,
            "mae": sum(absolute_errors) / denominator if denominator else None,
            "person_presence_accuracy": presence_correct / denominator if denominator else None,
            "person_presence": {**confusion, "precision": precision, "recall": recall, "f1": f1},
            "gte_accuracy": {n: {**value, "accuracy": value["correct"] / value["total"] if value["total"] else None}
                             for n, value in thresholds.items()},
            "elapsed_seconds": time.perf_counter() - started, "predictions": predictions}


def train_person(manifest_path: Path, workspace_root: Path, output_dir: Path,
                 profile: PersonTrainingProfile | None = None, *, device="cuda",
                 evaluate_test: bool = True):
    """Fit train; set evaluate_test=False while comparing candidate budgets.

    The True API default retains the original v1 call contract. The CLI defaults
    to False so new selection experiments do not automatically score audit data.
    """
    if type(evaluate_test) is not bool:
        raise ValueError("evaluate_test must be a bool")
    profile = profile or PersonTrainingProfile()
    root, output_dir = Path(workspace_root).resolve(), Path(output_dir).resolve()
    manifest_path = Path(manifest_path).resolve()
    manifest_hash = sha256_file(manifest_path)
    rows = load_jsonl(manifest_path)
    validation = validate_manifest(rows, root, require_split=True)
    if sha256_file(manifest_path) != manifest_hash:
        raise RuntimeError("manifest changed while loading training data")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError("training output directory must be new or empty")
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    torch.set_num_threads(4)
    random.seed(profile.seed)
    np.random.seed(profile.seed)
    torch.manual_seed(profile.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(profile.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    reviewed = [row for row in rows if row["person"]["count_status"] == "verified"
                and not row["person"]["iscrowd"] and row["person"]["boxes"] is not None
                and row.get("person_review", {}).get("detection_eligible") is True]
    subsets = {split: [row for row in reviewed if row["split"] == split] for split in ("train", "val", "test")}
    random.Random(profile.seed).shuffle(subsets["train"])
    subsets["train"] = subsets["train"][:profile.max_training_images]
    if not subsets["train"] or not any(row["person"]["count"] for row in subsets["train"]):
        raise ValueError("training needs reviewed examples including people")
    if not subsets["val"]:
        raise ValueError("a separate reviewed validation set is required")
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.hub.set_dir(str(root / "models/pretrained"))
    metadata = {"schema_version": 1, "architecture": "ssdlite320_mobilenet_v3_large",
                "profile": asdict(profile), "profile_frozen_before_fit": True,
                "manifest_sha256": manifest_hash, "manifest_validation": validation,
                "training_ids": [row["image_id"] for row in subsets["train"]],
                "training_images": len(subsets["train"]),
                "pretrained_weights": "SSDLite320_MobileNet_V3_Large_Weights.COCO_V1",
                "pretrained_source": SSDLite320_MobileNet_V3_Large_Weights.COCO_V1.url,
                "pretrained_overlap_notice": "COCO pretrained weights have already learned COCO training images. This small benchmark is not a from-scratch unseen-data estimate.",
                "input": {"size": 320, "channels": "RGB", "layout": "CHW", "range": [0, 1],
                          "resize": "whole-image letterbox", "padding_rgb": [114, 114, 114]},
                "postprocess": {"person_class_id": 1, "nms": "inside torchvision SSD", "box_units": "original image pixels"},
                "device": str(device), "torch_version": str(torch.__version__),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "school_data_used": False, "test_used_for_fitting_or_selection": False,
                "test_evaluated": evaluate_test}
    (output_dir / "frozen-profile.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    model = build_person_model(profile).to(device)
    cached = root / "models/pretrained/checkpoints" / Path(metadata["pretrained_source"]).name
    metadata["pretrained_file_sha256"] = sha256_file(cached)
    metadata["gpu_name"] = torch.cuda.get_device_name(device) if device.startswith("cuda") else None
    metadata["backbone_before_sha256"] = parameter_digest(model.backbone)
    metadata["trainable_parameters"] = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad),
                                 lr=profile.learning_rate, weight_decay=profile.weight_decay)
    loader = DataLoader(PersonDataset(subsets["train"], root, profile), batch_size=profile.batch_size,
                        shuffle=True, generator=torch.Generator().manual_seed(profile.seed),
                        collate_fn=lambda batch: tuple(zip(*batch)), num_workers=0)
    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)
        torch.cuda.synchronize(device)
    started, steps = time.perf_counter(), []
    for epoch in range(profile.epochs):
        set_person_training_mode(model)
        for images, targets in loader:
            images = [image.to(device) for image in images]
            targets = [{key: value.to(device) for key, value in target.items()} for target in targets]
            optimizer.zero_grad(set_to_none=True)
            losses = model(images, targets)
            loss = sum(losses.values())
            if not torch.isfinite(loss):
                raise RuntimeError("nonfinite person detection loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad), 10, error_if_nonfinite=True)
            optimizer.step()
            record = {"epoch": epoch + 1, "step": len(steps) + 1, "loss": float(loss.detach()),
                      **{name: float(value.detach()) for name, value in losses.items()}}
            steps.append(record)
            print(json.dumps(record), flush=True)
    if device.startswith("cuda"):
        torch.cuda.synchronize(device)
    metadata["fit_seconds"] = time.perf_counter() - started
    metadata["cuda_peak_allocated_bytes"] = torch.cuda.max_memory_allocated(device) if device.startswith("cuda") else None
    metadata["backbone_after_sha256"] = parameter_digest(model.backbone)
    if metadata["backbone_before_sha256"] != metadata["backbone_after_sha256"]:
        raise RuntimeError("frozen person backbone changed")
    if sha256_file(manifest_path) != manifest_hash:
        raise RuntimeError("manifest changed during fitting; refusing checkpoint")
    checkpoint = output_dir / "person.pt"
    state = {name: tensor.detach().cpu() for name, tensor in model.state_dict().items()}
    torch.save({"state_dict": state, "metadata": metadata}, checkpoint)
    metadata["checkpoint_sha256"] = sha256_file(checkpoint)
    reports = {split: evaluate_person(model, subsets[split], root, profile, device=device)
               for split in (("val", "test") if evaluate_test else ("val",))}
    report = {"metadata": metadata, "steps": steps, "evaluation": reports,
              "limitations": ["tiny reviewed COCO subset", "single automated visual reviewer", "COCO pretrained prior", "not school accuracy", "Pi and ONNX not tested"]}
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def load_person_checkpoint(path, *, device="cpu"):
    saved = torch.load(path, map_location="cpu", weights_only=True)
    metadata = saved["metadata"]
    profile = PersonTrainingProfile(**metadata["profile"])
    model = build_person_model(profile, pretrained=False)
    model.load_state_dict(saved["state_dict"], strict=True)
    model.to(device).eval()
    return model, profile, metadata
