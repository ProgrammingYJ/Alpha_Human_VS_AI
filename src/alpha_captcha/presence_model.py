"""Limited tree/building/pond transfer learning; inference accepts RGB pixels only.

Official references: torchvision MobileNetV3 Small / IMAGENET1K_V1,
PyTorch BCEWithLogitsLoss and Module.eval. We deliberately replace the published
center-crop transform with documented whole-image letterboxing for this task.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import time
from urllib.parse import urlparse

from PIL import Image, ImageOps
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset
import torchvision
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small
from torchvision.transforms import functional as TF

from .dataset import LABELS, load_jsonl, sha256_file, validate_manifest


ARCHITECTURE = "mobilenet_v3_small_presence_v1"
IMAGE_SIZE = 224
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
FILL = (124, 116, 104)
PREPROCESSING = {
    "size": IMAGE_SIZE, "color": "RGB", "layout": "NCHW", "dtype": "float32",
    "resize": "aspect_preserving_letterbox", "interpolation": "PIL_BILINEAR",
    "resized_dimension_rounding": "python_round_then_clamp_1_to_size",
    "padding": "center_floor_left_top", "fill_rgb": list(FILL),
    "exif_transpose": True, "pixel_scale": "divide_by_255",
    "mean": list(MEAN), "std": list(STD), "center_crop": False,
}


@dataclass(frozen=True)
class PresenceTrainingProfile:
    name: str = "presence-limited-v1"
    epochs: int = 1
    batch_size: int = 8
    max_train_images: int = 64
    seed: int = 42
    learning_rate: float = 0.001
    weight_decay: float = 0.01
    threshold: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("profile name must be a non-empty string")
        for key in ("epochs", "batch_size", "max_train_images"):
            if type(getattr(self, key)) is not int or getattr(self, key) <= 0:
                raise ValueError(f"{key} must be a positive integer, not bool")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer, not bool")
        for key in ("learning_rate", "weight_decay", "threshold"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{key} must be a finite number, not bool")
        if self.learning_rate <= 0 or self.weight_decay < 0 or not 0 <= self.threshold <= 1:
            raise ValueError("invalid learning rate, weight decay or threshold")


def letterbox_image(image: Image.Image, size: int = IMAGE_SIZE) -> Image.Image:
    if not isinstance(image, Image.Image):
        raise TypeError("inference input must be a PIL image, not a filename or record")
    if type(size) is not int or size <= 0:
        raise ValueError("size must be a positive integer")
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    width, height = rgb.size
    if min(width, height) <= 0:
        raise ValueError("image dimensions must be positive")
    scale = min(size / width, size / height)
    resized = (
        max(1, min(size, round(width * scale))),
        max(1, min(size, round(height * scale))),
    )
    canvas = Image.new("RGB", (size, size), FILL)
    canvas.paste(rgb.resize(resized, Image.Resampling.BILINEAR), (
        (size - resized[0]) // 2, (size - resized[1]) // 2,
    ))
    return canvas


def preprocess_image(image: Image.Image) -> torch.Tensor:
    tensor = TF.pil_to_tensor(letterbox_image(image)).to(dtype=torch.float32).div(255.0)
    return TF.normalize(tensor, MEAN, STD)


class PresenceNet(nn.Module):
    """Keep all feature parameters AND BatchNorm buffers frozen during fit."""

    def __init__(self, features: nn.Module, avgpool: nn.Module, classifier: nn.Module) -> None:
        super().__init__()
        self.features, self.avgpool, self.classifier = features, avgpool, classifier
        self.features.requires_grad_(False)
        self.features.eval()

    def train(self, mode: bool = True):
        super().train(mode)
        self.features.eval()
        return self

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            features = self.features(images)
        return self.classifier(torch.flatten(self.avgpool(features), 1))


def build_presence_model(*, pretrained: bool = True) -> tuple[PresenceNet, dict]:
    weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    base = mobilenet_v3_small(weights=weights, progress=True)
    base.classifier[-1] = nn.Linear(base.classifier[-1].in_features, len(LABELS))
    provenance = {"name": None, "url": None, "sha256": None, "dataset": None}
    if weights is not None:
        cached = Path(torch.hub.get_dir()) / "checkpoints" / Path(urlparse(weights.url).path).name
        digest = sha256_file(cached)
        # torchvision validates freshly downloaded weights; also check cache hits.
        expected_prefix = cached.stem.rsplit("-", 1)[-1]
        if not digest.startswith(expected_prefix):
            raise ValueError("cached official pretrained weights failed their SHA-256 prefix")
        provenance = {
            "name": "MobileNet_V3_Small_Weights.IMAGENET1K_V1",
            "url": weights.url, "sha256": digest, "dataset": "ImageNet-1K",
            "published_transform_replaced": "whole-image letterbox; no center crop",
        }
    return PresenceNet(base.features, base.avgpool, base.classifier), provenance


def state_sha256(module: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(str(tuple(value.shape)).encode("ascii"))
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


class PresenceDataset(Dataset):
    """Verify the entire development manifest before selecting one split."""

    def __init__(
        self, records: Sequence[dict], workspace_root: Path | str, split: str,
        *, max_images: int | None = None, seed: int = 42,
    ) -> None:
        if split not in {"train", "val", "test"}:
            raise ValueError("split must be train, val or test")
        self.root = Path(workspace_root).resolve()
        validate_manifest(records, self.root, require_split=True)
        if max_images is not None and (type(max_images) is not int or max_images <= 0):
            raise ValueError("max_images must be a positive integer or None")
        if max_images is not None and split != "train":
            raise ValueError("validation/test evaluation cannot be capped by the training budget")
        self.records = sorted(
            (row for row in records if row["split"] == split),
            key=lambda row: (row["dataset_ref"], str(row["dataset_version"]), row["image_id"]),
        )
        if max_images is not None and len(self.records) > max_images:
            shuffled = list(self.records)
            random.Random(seed).shuffle(shuffled)
            self.records = shuffled[:max_images]
        self.split = split

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        row = self.records[index]
        with Image.open(self.root / row["image_path"]) as image:
            pixels = preprocess_image(image)
        values = [row["labels"][label] for label in LABELS]
        target = torch.tensor([value is True for value in values], dtype=torch.float32)
        known = torch.tensor([value is not None for value in values], dtype=torch.bool)
        return pixels, target, known, index


def masked_bce_with_logits(logits: torch.Tensor, targets: torch.Tensor, known: torch.Tensor) -> torch.Tensor:
    if logits.shape != targets.shape or logits.shape != known.shape or logits.ndim != 2 or logits.shape[1] != 3:
        raise ValueError("logits, targets and known must have matching [N,3] shapes")
    if known.dtype != torch.bool:
        raise ValueError("known mask must have bool dtype")
    if not bool(torch.isfinite(logits).all()):
        raise ValueError("model logits must all be finite")
    known_targets = targets[known]
    if not bool(torch.isfinite(known_targets).all()) or not bool(((known_targets == 0) | (known_targets == 1)).all()):
        raise ValueError("known targets must be finite binary labels")
    if not bool(known.any()):
        return logits[known].sum()
    safe_targets = torch.where(known, targets, torch.zeros_like(targets))
    losses = F.binary_cross_entropy_with_logits(logits, safe_targets, reduction="none")
    return losses[known].mean()


def presence_metrics(
    probabilities: torch.Tensor, targets: torch.Tensor, known: torch.Tensor, *, threshold: float = 0.5,
) -> dict:
    PresenceTrainingProfile(threshold=threshold)
    if probabilities.shape != targets.shape or probabilities.shape != known.shape or probabilities.ndim != 2 or probabilities.shape[1] != 3:
        raise ValueError("metrics expect matching [N,3] tensors")
    if known.dtype != torch.bool or not bool(torch.isfinite(probabilities).all()) or not bool(((probabilities >= 0) & (probabilities <= 1)).all()):
        raise ValueError("invalid probabilities or known mask")
    if not bool(((targets[known] == 0) | (targets[known] == 1)).all()):
        raise ValueError("known targets must be binary")
    decisions = probabilities >= threshold
    truth = targets == 1

    def divide(numerator, denominator):
        return numerator / denominator if denominator else None

    result = {}
    for index, label in enumerate(LABELS):
        mask, positive, predicted = known[:, index], truth[:, index], decisions[:, index]
        tp = int((mask & positive & predicted).sum())
        fp = int((mask & ~positive & predicted).sum())
        fn = int((mask & positive & ~predicted).sum())
        tn = int((mask & ~positive & ~predicted).sum())
        total = tp + fp + fn + tn
        result[label] = {
            "known": total, "unknown": len(mask) - total, "positive": tp + fn, "negative": tn + fp,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": divide(tp, tp + fp), "recall": divide(tp, tp + fn),
            "f1": divide(2 * tp, 2 * tp + fp + fn), "accuracy": divide(tp + tn, total),
        }
    return {"threshold": threshold, "threshold_source": "preset_no_validation_tuning", "classes": result}


def evaluate_presence(model: PresenceNet, dataset: PresenceDataset, device, *, batch_size: int = 8, threshold: float = 0.5) -> tuple[dict, list[dict]]:
    model.eval()
    score_batches, target_batches, mask_batches, predictions = [], [], [], []
    with torch.inference_mode():
        for pixels, target, known, indices in DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0):
            logits = model(pixels.to(device))
            if not bool(torch.isfinite(logits).all()):
                raise ValueError("nonfinite evaluation logits")
            scores = logits.sigmoid().cpu()
            score_batches.append(scores)
            target_batches.append(target)
            mask_batches.append(known)
            for index, score in zip(indices.tolist(), scores.tolist()):
                row = dataset.records[index]
                predictions.append({
                    "image_id": row["image_id"], "image_path": row["image_path"], "split": dataset.split,
                    "scores": dict(zip(LABELS, score)),
                    "decisions": {label: value >= threshold for label, value in zip(LABELS, score)},
                    "targets_for_evaluator_only": row["labels"],
                })
    scores = torch.cat(score_batches) if score_batches else torch.empty((0, 3))
    targets = torch.cat(target_batches) if target_batches else torch.empty((0, 3))
    masks = torch.cat(mask_batches) if mask_batches else torch.empty((0, 3), dtype=torch.bool)
    result = presence_metrics(scores, targets, masks, threshold=threshold)
    result["images"] = len(dataset)
    result["metric_zero_denominator"] = "null; no unsupported accuracy claim"
    return result, predictions


def _device(value: str | torch.device) -> torch.device:
    device = torch.device(value)
    if device.type not in {"cpu", "cuda"}:
        raise ValueError("only CPU and CUDA are supported by this baseline")
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable; no silent CPU fallback")
    return device


def _write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def train_presence(
    manifest_path: Path | str, workspace_root: Path | str, output_dir: Path | str,
    *, profile: PresenceTrainingProfile | None = None, device: str = "cuda",
    evaluate_test: bool = True,
) -> dict:
    """Fit ONLY train for a fixed budget, then evaluate each unchanged split.

    Use evaluate_test=False for candidate selection; CLI defaults to that mode.
    The True API default preserves the original fixed-v1 training contract.
    No best-checkpoint selection, early stopping or threshold search. All
    metadata and evaluation answers are separate from pixel-only prediction.
    Existing output directories are never reused or overwritten.
    """
    started = time.perf_counter()
    if type(evaluate_test) is not bool:
        raise ValueError("evaluate_test must be a bool")
    profile = profile or PresenceTrainingProfile()
    if not isinstance(profile, PresenceTrainingProfile):
        raise ValueError("profile must be a PresenceTrainingProfile")
    manifest_path, root, output_dir = Path(manifest_path), Path(workspace_root).resolve(), Path(output_dir)
    manifest_digest = sha256_file(manifest_path)
    records = load_jsonl(manifest_path)
    if sha256_file(manifest_path) != manifest_digest:
        raise ValueError("manifest changed while being loaded")
    validation = validate_manifest(records, root, require_split=True)
    datasets = {
        split: PresenceDataset(records, root, split, max_images=profile.max_train_images if split == "train" else None, seed=profile.seed)
        for split in (("train", "val", "test") if evaluate_test else ("train", "val"))
    }
    train = datasets["train"]
    if not len(train):
        raise ValueError("no train images; val/test may never be used to fit")
    for label in LABELS:
        if not any(row["labels"][label] is not None for row in train.records):
            raise ValueError(f"training label {label} has no known supervision")
    if output_dir.exists():
        raise FileExistsError(f"use a new output directory: {output_dir}")
    target_device = _device(device)
    random.seed(profile.seed)
    torch.manual_seed(profile.seed)
    if target_device.type == "cuda":
        torch.cuda.manual_seed_all(profile.seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
    torch.hub.set_dir(str(root / "models/pretrained"))
    model, pretrained = build_presence_model(pretrained=True)
    model.to(target_device)
    before_features = state_sha256(model.features)
    before_classifier = state_sha256(model.classifier)
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    frozen_at = datetime.now(timezone.utc)
    output_key = hashlib.sha256(str(output_dir.resolve()).encode("utf-8")).hexdigest()[:12]
    frozen_path = root / "runs/frozen-profiles" / (
        f"presence-{output_key}-{manifest_digest[:12]}-{frozen_at.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    )
    frozen_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(frozen_path, {
        "format_version": 1, "architecture": ARCHITECTURE,
        "created_at_utc": frozen_at.isoformat(), "recorded_before_optimizer_creation": True,
        "output_directory": str(output_dir.resolve()), "manifest_sha256": manifest_digest,
        "profile": asdict(profile), "optimizer": "AdamW", "features_frozen_and_eval": True,
        "pretrained": pretrained, "preprocessing": PREPROCESSING,
        "threshold_source": "preset_no_validation_tuning",
        "train_images": len(train), "fit_split": "train_only", "school_data_used": False,
        "test_evaluated": evaluate_test,
    })
    optimizer = torch.optim.AdamW(trainable, lr=profile.learning_rate, weight_decay=profile.weight_decay)
    generator = torch.Generator().manual_seed(profile.seed)
    loader = DataLoader(train, batch_size=profile.batch_size, shuffle=True, generator=generator, num_workers=0)
    if target_device.type == "cuda":
        torch.cuda.synchronize(target_device)
        torch.cuda.reset_peak_memory_stats(target_device)
    setup_seconds = time.perf_counter() - started
    fit_started = time.perf_counter()
    history = []
    for epoch in range(profile.epochs):
        model.train()
        total_loss, known_labels, steps, skipped = 0.0, 0, 0, 0
        for pixels, targets, known, _ in loader:
            if not bool(known.any()):
                skipped += 1
                continue
            optimizer.zero_grad(set_to_none=True)
            targets, known = targets.to(target_device), known.to(target_device)
            loss = masked_bce_with_logits(model(pixels.to(target_device)), targets, known)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError("nonfinite training loss")
            loss.backward()
            if any(parameter.grad is not None and not bool(torch.isfinite(parameter.grad).all()) for parameter in trainable):
                raise RuntimeError("nonfinite classifier gradients")
            optimizer.step()
            count = int(known.sum().item())
            total_loss += float(loss.item()) * count
            known_labels += count
            steps += 1
        if not steps:
            raise ValueError("all training labels were unknown; no optimizer step performed")
        history.append({"epoch": epoch + 1, "loss": total_loss / known_labels, "known_labels": known_labels, "optimizer_steps": steps, "skipped_unknown_batches": skipped})
    if target_device.type == "cuda":
        torch.cuda.synchronize(target_device)
    fit_seconds = time.perf_counter() - fit_started
    peak_mib = torch.cuda.max_memory_allocated(target_device) / 1024**2 if target_device.type == "cuda" else None
    after_features = state_sha256(model.features)
    after_classifier = state_sha256(model.classifier)
    if before_features != after_features:
        raise RuntimeError("frozen features or BatchNorm buffers changed")
    evaluated = {}
    predictions = {}
    eval_started = time.perf_counter()
    for split, dataset in datasets.items():
        evaluated[split], predictions[split] = evaluate_presence(model, dataset, target_device, batch_size=profile.batch_size, threshold=profile.threshold)
    if state_sha256(model.classifier) != after_classifier or state_sha256(model.features) != after_features:
        raise RuntimeError("evaluation changed model parameters/buffers")
    if target_device.type == "cuda":
        torch.cuda.synchronize(target_device)
    eval_seconds = time.perf_counter() - eval_started
    if sha256_file(manifest_path) != manifest_digest:
        raise ValueError("manifest changed during training; refusing misleading provenance")
    metadata = {
        "format_version": 1, "architecture": ARCHITECTURE, "labels": list(LABELS),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preprocessing": PREPROCESSING, "outputs": "three_logits; independent sigmoid at prediction",
        "pretrained": pretrained, "profile": asdict(profile), "optimizer": "AdamW",
        "frozen_profile_path": str(frozen_path), "frozen_profile_sha256": sha256_file(frozen_path),
        "manifest_sha256": manifest_digest, "development_validation": validation,
        "train_used": [{"dataset_ref": row["dataset_ref"], "image_id": row["image_id"], "sha256": row["sha256"]} for row in train.records],
        "fit_split": "train_only", "early_stopping": False, "model_selection": "fixed_last_epoch",
        "threshold_source": "preset_no_validation_tuning", "school_data_used": False,
        "test_evaluated": evaluate_test,
        "trainable_parameters": sum(parameter.numel() for parameter in trainable),
        "total_parameters": sum(parameter.numel() for parameter in model.parameters()),
        "trainable_parameter_names": [name for name, parameter in model.named_parameters() if parameter.requires_grad],
        "features_sha256_before": before_features, "features_sha256_after": after_features,
        "features_and_bn_unchanged": before_features == after_features,
        "classifier_sha256_before": before_classifier, "classifier_sha256_after": after_classifier,
        "model_state_sha256": state_sha256(model), "history": history, "evaluations": evaluated,
        "environment": {"python": platform.python_version(), "torch": str(torch.__version__), "torchvision": str(torchvision.__version__)},
        "device": {"requested": str(device), "actual": str(next(model.parameters()).device),
                   "name": torch.cuda.get_device_name(target_device) if target_device.type == "cuda" else platform.processor(),
                   "peak_training_allocated_mib": peak_mib},
        "timing": {"setup_including_weight_download_seconds": setup_seconds, "fit_wall_seconds": fit_seconds,
                   "evaluation_wall_seconds": eval_seconds, "wall_seconds_before_artifact_save": time.perf_counter() - started},
        "reproducibility": "seeded; exact bitwise reproducibility across devices is not claimed",
        "limitations": ["tiny selected Kaggle development sample, not school accuracy", "no ONNX or Pi benchmark", "no screen capture or mouse control"],
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    checkpoint = output_dir / "presence.pt"
    state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    with checkpoint.open("xb") as stream:
        torch.save({"state_dict": state, "metadata": metadata}, stream)
    report = {**metadata, "checkpoint": str(checkpoint), "checkpoint_sha256": sha256_file(checkpoint)}
    _write_json(output_dir / "report.json", report)
    for split in datasets:
        _write_json(output_dir / f"predictions-{split}.json", predictions[split])
    return report


def load_presence_checkpoint(path: Path | str, *, device: str = "cpu") -> tuple[PresenceNet, dict]:
    payload = torch.load(Path(path), map_location="cpu", weights_only=True)
    metadata = payload["metadata"]
    if metadata.get("format_version") != 1 or metadata.get("architecture") != ARCHITECTURE or metadata.get("labels") != list(LABELS):
        raise ValueError("unsupported presence checkpoint architecture/label order")
    if metadata.get("preprocessing") != PREPROCESSING:
        raise ValueError("checkpoint preprocessing differs from the implemented pixel contract")
    model, _ = build_presence_model(pretrained=False)
    model.load_state_dict(payload["state_dict"], strict=True)
    if state_sha256(model) != metadata.get("model_state_sha256"):
        raise ValueError("checkpoint state hash mismatch")
    model.to(_device(device)).eval()
    return model, metadata


def predict_presence(
    model: PresenceNet, images: Sequence[Image.Image], *, device: str | None = None, batch_size: int = 8,
) -> list[dict[str, float]]:
    """Only PIL pixels enter the model; no filenames, source IDs or answer data."""
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    if any(not isinstance(image, Image.Image) for image in images):
        raise TypeError("predict_presence accepts PIL images only")
    target_device = _device(device) if device is not None else next(model.parameters()).device
    model.to(target_device).eval()
    result = []
    with torch.inference_mode():
        for start in range(0, len(images), batch_size):
            pixels = torch.stack([preprocess_image(image) for image in images[start:start + batch_size]])
            logits = model(pixels.to(target_device))
            if logits.ndim != 2 or logits.shape[1] != len(LABELS) or not bool(torch.isfinite(logits).all()):
                raise ValueError("model must produce finite three-class logits")
            result.extend(dict(zip(LABELS, values)) for values in logits.sigmoid().cpu().tolist())
    return result
