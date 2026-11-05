"""Pixel-only PyTorch tile inference. ONNX and live capture remain separate."""

from collections.abc import Sequence
import copy
from typing import Protocol
import time

from .tasks import TaskCondition, TilePrediction, select_tiles


def split_grid_image(image):
    """Split a saved, borderless 3x3 grid into nine independent RGB tiles."""
    from PIL import Image
    if not isinstance(image, Image.Image):
        raise TypeError("grid input must be PIL pixels")
    rgb = image.convert("RGB")
    width, height = rgb.size
    if min(width, height) < 3:
        raise ValueError("grid image must have at least three pixels per axis")
    return [rgb.crop((column * width // 3, row * height // 3,
                      (column + 1) * width // 3, (row + 1) * height // 3))
            for row in range(3) for column in range(3)]


class TorchTilePredictor:
    """Read no answer files or metadata from a site; both models receive RGB."""

    def __init__(self, presence_model, presence_metadata, person_model, person_profile, *, device="cpu"):
        self.presence_model = presence_model
        self.presence_metadata = presence_metadata
        self.person_model = person_model
        self.person_profile = person_profile
        self.device = device
        self._prepare_models = True

    def fork_for_inference(self):
        """Share prepared eval weights while isolating a worker's mutable context.

        Call before dispatching concurrent work. Checkpoint loading already moves
        both models to their final device; workers must never change train/eval
        state or move shared parameters during inference.
        """
        import torch
        target_device = torch.device(self.device)
        for model in (self.presence_model, self.person_model):
            if any(module.training for module in model.modules()):
                raise ValueError("shared inference models must already be in evaluation mode")
            for tensor in (*model.parameters(), *model.buffers()):
                if (tensor.device.type != target_device.type
                        or target_device.index is not None and tensor.device.index != target_device.index):
                    raise ValueError("shared inference models must already be on the requested device")
        worker = copy.copy(self)
        worker.presence_metadata = copy.deepcopy(self.presence_metadata)
        worker._prepare_models = False
        return worker

    fork_for_worker = fork_for_inference

    def _inference_options(self):
        # Preserve the existing serial API and its preparation defaults.
        return {} if self._prepare_models else {"prepare_model": False}

    @classmethod
    def from_checkpoints(cls, presence_checkpoint, person_checkpoint, *, device="cpu"):
        from .presence_model import load_presence_checkpoint
        from .person_model import load_person_checkpoint
        presence, metadata = load_presence_checkpoint(presence_checkpoint, device=device)
        person, profile, _ = load_person_checkpoint(person_checkpoint, device=device)
        return cls(presence, metadata, person, profile, device=device)

    def predict_tiles(self, images):
        from PIL import Image
        from .presence_model import predict_presence
        from .person_model import predict_person
        if len(images) != 9 or any(not isinstance(image, Image.Image) for image in images):
            raise ValueError("exactly nine PIL RGB tile images are required")
        options = self._inference_options()
        scores = predict_presence(self.presence_model, images, device=self.device, **options)
        people = predict_person(self.person_model, images, self.person_profile, device=self.device, **options)
        return [TilePrediction(presence_scores=score, person_count=person["person_count"])
                for score, person in zip(scores, people)]

    def predict_condition_tiles(self, images, condition: TaskCondition):
        """Run the frozen model needed by the public question only.

        The full predict_tiles API remains available for offline evaluation.
        Unused outputs are unknown rather than invented negative predictions.
        Model weights, preprocessing and postprocessing remain identical.
        """
        from PIL import Image
        from .presence_model import predict_presence
        from .person_model import predict_person
        from .tasks import PRESENCE_TASKS
        if (not isinstance(condition, TaskCondition) or len(images) != 9
                or any(not isinstance(image, Image.Image) for image in images)):
            raise ValueError("public condition and exactly nine PIL RGB tiles required")
        if condition.task_type in PRESENCE_TASKS:
            scores = predict_presence(self.presence_model, images, device=self.device, **self._inference_options())
            return [TilePrediction(presence_scores=score) for score in scores]
        people = predict_person(self.person_model, images, self.person_profile, device=self.device, **self._inference_options())
        return [TilePrediction(person_count=person["person_count"]) for person in people]

    def solve_grid(self, image, condition: TaskCondition):
        tiles = split_grid_image(image)
        started = time.perf_counter()
        predictions = self.predict_tiles(tiles)
        elapsed = time.perf_counter() - started
        threshold = self.presence_metadata["profile"]["threshold"]
        selected = select_tiles(predictions, condition, {name: threshold for name in ("tree", "building", "pond")})
        return {"source": "trained_pytorch_rgb_models", "selected_tiles": selected,
                "predictions": [{"presence_scores": dict(row.presence_scores), "person_count": row.person_count}
                                for row in predictions],
                "inference_wall_seconds": elapsed, "timing_note": "one invocation including preprocessing; not a p50/p95 benchmark",
                "capture_performed": False, "mouse_control_performed": False}


class TileClassifier(Protocol):
    def predict_scores(self, tile_rgb_images: Sequence[object], target_label: str) -> list[float]:
        """Return target-label scores in tile order; preprocessing is model metadata."""
        ...
