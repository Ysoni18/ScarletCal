"""Data-driven instructional calendar; no parsing or event generation."""

from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from scarletcal.domain.models import Weekday


@dataclass(frozen=True)
class InstructionalOverride:
    date: date
    weekday: Weekday | None
    reason: str

    def __post_init__(self) -> None:
        if type(self.date) is not date:
            raise ValueError("Override date must be a date, not a datetime.")
        if self.weekday is not None and not isinstance(self.weekday, Weekday):
            raise ValueError("Override weekday must be Weekday or None (no classes).")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Override reason is required.")


@dataclass(frozen=True)
class AcademicTerm:
    term: str
    campus: str
    instruction_start: date
    instruction_end: date
    instructional_overrides: tuple[InstructionalOverride, ...]
    timezone: str
    source: str
    verified_on: date

    def __post_init__(self) -> None:
        for name in ("instruction_start", "instruction_end", "verified_on"):
            if type(getattr(self, name)) is not date:
                raise ValueError(f"{name} must be a date, not a datetime.")
        if self.instruction_end < self.instruction_start:
            raise ValueError("Instruction end must be on or after instruction start.")
        for name in ("term", "campus", "timezone", "source"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string.")
        ZoneInfo(self.timezone)
        # Copy to a tuple so caller-owned lists cannot mutate a frozen term.
        overrides = tuple(self.instructional_overrides)
        seen: set[date] = set()
        for override in overrides:
            if not isinstance(override, InstructionalOverride):
                raise ValueError("Expected InstructionalOverride objects.")
            if not self.instruction_start <= override.date <= self.instruction_end:
                raise ValueError(f"Override {override.date} is outside the instructional term.")
            if override.date in seen:
                raise ValueError(f"Duplicate override date: {override.date}.")
            seen.add(override.date)
        object.__setattr__(self, "instructional_overrides", overrides)

    def effective_instructional_day(self, day: date) -> Weekday | None:
        """Return the replacement weekday, normal weekday, or None for no classes.

        Term boundaries are inclusive. Weekends are ordinary weekdays unless
        explicitly overridden, so actual Saturday/Sunday meetings are preserved.
        """
        if type(day) is not date:
            raise ValueError("Expected a physical calendar date, not a datetime.")
        if not self.instruction_start <= day <= self.instruction_end:
            return None
        for override in self.instructional_overrides:
            if override.date == day:
                return override.weekday
        return tuple(Weekday)[day.weekday()]
