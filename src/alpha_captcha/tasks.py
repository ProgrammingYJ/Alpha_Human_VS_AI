"""Public challenge conditions and deterministic selection, with no answer access."""

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence
import math
from types import MappingProxyType


PRESENCE_TASKS = {
    "tree_present": "tree", "building_present": "building", "pond_present": "pond",
}
TASK_TYPES = frozenset((*PRESENCE_TASKS, "person_present", "person_count"))


@dataclass(frozen=True)
class TaskCondition:
    task_type: str
    operator: str | None = None
    n: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_type, str) or self.task_type not in TASK_TYPES:
            raise ValueError(f"unsupported task_type: {self.task_type}")
        if self.task_type == "person_count":
            if self.operator not in {"eq", "gte"}:
                raise ValueError("person_count requires explicit operator 'eq' or 'gte'")
            if type(self.n) is not int or self.n <= 0:
                raise ValueError("n must be a positive integer (booleans excluded)")
            if not 2 <= self.n <= 5:
                raise ValueError("the confirmed booth range is n=2..5")
        elif self.operator is not None or self.n is not None:
            raise ValueError("operator and n are only valid for person_count")

    @classmethod
    def from_dict(cls, value: Mapping) -> "TaskCondition":
        if not isinstance(value, Mapping):
            raise ValueError("condition must be an object")
        if set(value) - {"task_type", "operator", "n"}:
            raise ValueError("only public task_type/operator/n fields are accepted")
        if "task_type" not in value:
            raise ValueError("task_type is required")
        return cls(**value)


@dataclass(frozen=True)
class TilePrediction:
    """A model result only. Unknown values remain None, never a guessed negative."""

    presence_scores: Mapping[str, float | None] = field(default_factory=dict)
    person_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.presence_scores, Mapping):
            raise ValueError("presence_scores must be a mapping")
        if set(self.presence_scores) - set(PRESENCE_TASKS.values()):
            raise ValueError("unsupported presence score label")
        for score in self.presence_scores.values():
            if score is not None and (
                isinstance(score, bool) or not isinstance(score, (float, int))
                or not math.isfinite(score) or not 0 <= score <= 1
            ):
                raise ValueError("scores must be finite probabilities in [0, 1] or None")
        object.__setattr__(self, "presence_scores", MappingProxyType(dict(self.presence_scores)))
        if self.person_count is not None and (
            type(self.person_count) is not int or self.person_count < 0
        ):
            raise ValueError("person_count must be a non-negative integer or None")


def select_tiles(
    predictions: Sequence[TilePrediction],
    condition: TaskCondition,
    thresholds: Mapping[str, float] | None = None,
) -> list[int]:
    """Apply a frozen condition to exactly nine predictions; never force top-k."""
    if len(predictions) != 9:
        raise ValueError("the challenge requires exactly 9 tile predictions")
    if not isinstance(condition, TaskCondition):
        raise ValueError("condition must be a TaskCondition")
    if any(not isinstance(item, TilePrediction) for item in predictions):
        raise ValueError("all predictions must be TilePrediction objects")
    selected = []
    if condition.task_type in PRESENCE_TASKS:
        label = PRESENCE_TASKS[condition.task_type]
        threshold = (thresholds or {}).get(label)
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or (
            not math.isfinite(threshold) or not 0 <= threshold <= 1
        ):
            raise ValueError(f"an explicit frozen threshold is required for {label}")
        for index, prediction in enumerate(predictions):
            score = prediction.presence_scores.get(label)
            if score is None:
                raise ValueError(f"tile {index}: {label} prediction is unknown")
            if score >= threshold:
                selected.append(index)
    else:
        for index, prediction in enumerate(predictions):
            count = prediction.person_count
            if count is None:
                raise ValueError(f"tile {index}: person_count prediction is unknown")
            matches = count >= 1 if condition.task_type == "person_present" else (
                count == condition.n if condition.operator == "eq" else count >= condition.n
            )
            if matches:
                selected.append(index)
    return selected
