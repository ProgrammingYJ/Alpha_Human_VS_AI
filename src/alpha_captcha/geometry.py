"""Pure geometry for a calibrated, fixed image-tile grid."""

from dataclasses import dataclass
from collections.abc import Iterable


@dataclass(frozen=True)
class GridLayout:
    left: int
    top: int
    width: int
    height: int
    rows: int
    columns: int
    gap_x: int = 0
    gap_y: int = 0

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if type(value) is not int:
                raise ValueError(f"{name}: an integer is required (booleans excluded)")
            if value < 0:
                raise ValueError(f"{name}: negative values are not supported")
        if min(self.width, self.height, self.rows, self.columns) <= 0:
            raise ValueError("width, height, rows and columns must be positive")
        if self.width - (self.columns - 1) * self.gap_x < self.columns:
            raise ValueError("grid width must leave at least one pixel per tile")
        if self.height - (self.rows - 1) * self.gap_y < self.rows:
            raise ValueError("grid height must leave at least one pixel per tile")

    def center(self, tile_index: int) -> tuple[int, int]:
        """Return a physical pixel center, in zero-based row-major order."""
        if type(tile_index) is not int:
            raise ValueError("tile index must be an integer")
        if not 0 <= tile_index < self.rows * self.columns:
            raise ValueError(f"tile index must be in [0, {self.rows * self.columns - 1}]")
        row, column = divmod(tile_index, self.columns)
        tile_width = (self.width - (self.columns - 1) * self.gap_x) / self.columns
        tile_height = (self.height - (self.rows - 1) * self.gap_y) / self.rows
        return (
            int(self.left + column * (tile_width + self.gap_x) + tile_width / 2),
            int(self.top + row * (tile_height + self.gap_y) + tile_height / 2),
        )

    def plan(self, tile_indices: Iterable[int]) -> list[dict[str, int]]:
        """Preserve input order and reject duplicate tile selection."""
        result: list[dict[str, int]] = []
        seen: set[int] = set()
        for tile_index in tile_indices:
            x, y = self.center(tile_index)
            if tile_index in seen:
                raise ValueError(f"duplicate tile index: {tile_index}")
            seen.add(tile_index)
            result.append({"tile_index": tile_index, "x": x, "y": y})
        return result
