"""Common training contracts; implementations live in presence_model/person_model.

ONNX exporting is the next stage and is not implemented by this Protocol.
"""

from pathlib import Path
from typing import Protocol


class Trainer(Protocol):
    def train(self, manifest: Path, output_dir: Path) -> Path:
        """Train from a grouped data manifest and return a checkpoint path."""
        ...


class ModelExporter(Protocol):
    def export_onnx(self, checkpoint: Path, output_dir: Path) -> Path:
        """Export model plus label/preprocessing metadata; parity must be checked."""
        ...
