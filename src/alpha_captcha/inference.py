"""Pixel-only PyTorch tile inference. ONNX and live capture remain separate."""

from collections.abc import Sequence
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
        scores = predict_presence(self.presence_model, images, device=self.device)
        people = predict_person(self.person_model, images, self.person_profile, device=self.device)
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
            scores = predict_presence(self.presence_model, images, device=self.device)
            return [TilePrediction(presence_scores=score) for score in scores]
        people = predict_person(self.person_model, images, self.person_profile, device=self.device)
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
