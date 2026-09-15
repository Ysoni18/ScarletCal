"""Deterministic parsing of the supported WebReg plain-text clipboard format.

Meeting support currently covers building-room locations on Busch and Livingston.
Unknown formats (including online, arranged, or asynchronous meetings) fail explicitly.
"""

import re
from datetime import time

from scarletcal.domain.models import Course, MeetingPattern, Weekday


_COURSE_HEADER_RE = re.compile(
    r"(?P<title>\S[^\r\n]*?)[ \t]+"
    r"\((?P<course_code>[0-9]{2}:[0-9]{3}:[0-9]{3})\)[ \t]+"
    r"Section[ \t]+(?P<section>[A-Za-z0-9]+)[ \t]+\|[ \t]+"
    r"\[(?P<index>[0-9]{5})\][ \t]+"
    r"Credits:[ \t]+(?P<credits>[0-9]+\.[0-9]+)"
)
_TIME_PATTERN = r"(?:[1-9]|1[0-2]):[0-5][0-9][ \t]+(?:AM|PM)"
_MEETING_RE = re.compile(
    r"(?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[ \t]+"
    rf"(?P<start>{_TIME_PATTERN})[ \t]+-[ \t]+"
    rf"(?P<end>{_TIME_PATTERN})[ \t]+"
    r"(?P<location>[A-Za-z0-9]+-[A-Za-z0-9]+)[ \t]+"
    r"(?P<campus>Busch|Livingston)"
)
_KNOWN_NOISE = frozenset({
    "Registered CoursesOnline Bill Payment View / Print Schedule",
})


class WebRegParseError(ValueError):
    """Input cannot be interpreted confidently as a supported WebReg schedule."""


def parse_course_header(line: str) -> dict[str, str | float] | None:
    """Return header metadata, or None when the line is not a course header."""
    match = _COURSE_HEADER_RE.fullmatch(line.strip())
    if match is None:
        return None

    return {
        "title": " ".join(match.group("title").split()),
        "course_code": match.group("course_code"),
        "section": match.group("section"),
        "index": match.group("index"),
        "credits": float(match.group("credits")),
    }


def _parse_time(value: str) -> time:
    """Convert an already validated 12-hour clock value without locale dependence."""
    clock, meridiem = value.split()
    hour, minute = map(int, clock.split(":"))
    return time(hour % 12 + (12 if meridiem == "PM" else 0), minute)


def parse_meeting(line: str) -> MeetingPattern:
    """Parse one meeting; raise WebRegParseError for invalid or unsupported input.

    Only same-day meetings with an end time later than their start are supported.
    """
    match = _MEETING_RE.fullmatch(line.strip())
    if match is None:
        raise WebRegParseError(
            "Invalid or unsupported meeting. Expected a weekday, "
            "h:mm AM/PM - h:mm AM/PM, building-room, and Busch or Livingston."
        )
    start = _parse_time(match.group("start"))
    end = _parse_time(match.group("end"))
    if end <= start:
        raise WebRegParseError("Meeting end time must be later than its start time.")
    return MeetingPattern(
        weekday=Weekday(match.group("weekday")),
        start_time=start,
        end_time=end,
        location=match.group("location"),
        campus=match.group("campus"),
    )


def parse_webreg_schedule(text: str) -> tuple[Course, ...]:
    """Scan headers and meetings in order, returning immutable Course objects.

    Blank lines and the exact observed navigation banner are ignored. Every other
    line must parse successfully; no partial schedule is returned on failure.
    Duplicate headers and identical meetings are rejected to prevent duplicate events.
    """
    courses: list[Course] = []
    header = None
    header_line = 0
    meetings: list[MeetingPattern] = []
    seen_indexes: set[str] = set()

    def finish_course() -> None:
        if header is None:
            return
        if not meetings:
            raise WebRegParseError(
                f"Line {header_line}: Course {header['course_code']} has no supported timed meetings."
            )
        courses.append(Course(**header, meetings=tuple(meetings)))

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line in _KNOWN_NOISE:
            continue
        parsed_header = parse_course_header(line)
        if parsed_header is not None:
            finish_course()
            index = parsed_header["index"]
            if index in seen_indexes:
                raise WebRegParseError(f"Line {line_number}: Duplicate course index {index}.")
            seen_indexes.add(index)
            header = parsed_header
            header_line = line_number
            meetings = []
            continue
        try:
            meeting = parse_meeting(line)
        except WebRegParseError as error:
            raise WebRegParseError(f"Line {line_number}: {error} Input: {line!r}") from error
        if header is None:
            raise WebRegParseError(f"Line {line_number}: Meeting appears before a course header.")
        if meeting in meetings:
            raise WebRegParseError(f"Line {line_number}: Duplicate meeting for this course.")
        meetings.append(meeting)

    finish_course()
    if not courses:
        raise WebRegParseError("No courses found. Paste a registered WebReg schedule.")
    return tuple(courses)
