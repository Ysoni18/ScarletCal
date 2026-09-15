"""Generate exact class occurrences from courses and an academic term."""

from .engine import SchedulingError, generate_occurrences

__all__ = ["SchedulingError", "generate_occurrences"]
