"""Future screenshot and input adapters; live input is deliberately unimplemented."""

from typing import Protocol


class ScreenCapture(Protocol):
    def capture_grid(self) -> object:
        """Capture only the calibrated image grid, without challenge answer data."""
        ...


class TileController(Protocol):
    def click_tiles(self, indices: list[int]) -> None:
        """Act on the owned booth screen after OS/session and coordinate checks."""
        ...
