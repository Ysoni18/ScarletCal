"""Load validated calendar data from JSON files or bundled Rutgers terms."""

import json
import re
from datetime import date
from importlib.resources import files
from pathlib import Path
from zoneinfo import ZoneInfoNotFoundError

from scarletcal.academic_calendar.models import AcademicTerm, InstructionalOverride
from scarletcal.domain.models import Weekday


class CalendarDataError(ValueError):
    """Calendar data is missing, unsupported, or internally inconsistent."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CalendarDataError(f"Duplicate JSON key: {key}.")
        result[key] = value
    return result


def _keys(value: object, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise CalendarDataError(f"{label} must contain exactly: {', '.join(sorted(expected))}.")


def _date(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise CalendarDataError("Dates must use YYYY-MM-DD strings.")
    return date.fromisoformat(value)


def _decode(text: str) -> AcademicTerm:
    try:
        data = json.loads(text, object_pairs_hook=_unique_object)
        _keys(data, {
            "term", "campus", "instruction_start", "instruction_end",
            "instructional_overrides", "timezone", "source", "verified_on",
        }, "Academic term")
        if not isinstance(data["instructional_overrides"], list):
            raise CalendarDataError("instructional_overrides must be a list.")
        overrides = []
        for entry in data["instructional_overrides"]:
            _keys(entry, {"date", "weekday", "reason"}, "Override")
            overrides.append(InstructionalOverride(
                date=_date(entry["date"]),
                weekday=None if entry["weekday"] is None else Weekday(entry["weekday"]),
                reason=entry["reason"],
            ))
        return AcademicTerm(
            term=data["term"],
            campus=data["campus"],
            instruction_start=_date(data["instruction_start"]),
            instruction_end=_date(data["instruction_end"]),
            instructional_overrides=tuple(overrides),
            timezone=data["timezone"],
            source=data["source"],
            verified_on=_date(data["verified_on"]),
        )
    except CalendarDataError:
        raise
    except (ValueError, TypeError, ZoneInfoNotFoundError) as error:
        raise CalendarDataError(f"Invalid academic calendar data: {error}") from error


def load_academic_term(path: str | Path) -> AcademicTerm:
    """Load an external JSON term; validation does not certify its source accuracy."""
    try:
        return _decode(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise CalendarDataError(f"Cannot read academic calendar {path}: {error}") from error


def load_rutgers_term(term: str) -> AcademicTerm:
    """Load a bundled New Brunswick standard-calendar term, e.g. 'fall-2026'."""
    if not isinstance(term, str) or not re.fullmatch(r"(?:fall|spring)-[0-9]{4}", term):
        raise CalendarDataError("Expected a term identifier such as 'fall-2026'.")
    resource = files("scarletcal").joinpath(
        "data", "rutgers", "new_brunswick", term.replace("-", "_") + ".json"
    )
    try:
        result = _decode(resource.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise CalendarDataError(f"Bundled Rutgers term is unavailable: {term}.") from error
    if result.term != term or result.campus != "new_brunswick":
        raise CalendarDataError("Bundled calendar identity does not match the requested term.")
    return result
