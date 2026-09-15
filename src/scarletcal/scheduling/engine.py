"""Generate occurrences without knowing Rutgers-specific dates or rules."""

from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from scarletcal.academic_calendar.models import AcademicTerm
from scarletcal.domain.models import ClassOccurrence, Course, Weekday


class SchedulingError(ValueError):
    """A meeting cannot be safely expanded into exact occurrences."""


def _local_datetime(day: date, clock: time, zone: ZoneInfo) -> datetime:
    """Reject nonexistent or ambiguous wall times instead of guessing across DST."""
    naive = datetime.combine(day, clock)
    candidates = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        roundtrip = candidate.astimezone(UTC).astimezone(zone)
        if roundtrip.replace(tzinfo=None) == naive:
            candidates.append(candidate)
    if not candidates:
        raise SchedulingError(f"Nonexistent local time: {naive} in {zone.key}.")
    if len({candidate.utcoffset() for candidate in candidates}) > 1:
        raise SchedulingError(f"Ambiguous local time: {naive} in {zone.key}.")
    return candidates[0]


def generate_occurrences(
    courses: Iterable[Course], term: AcademicTerm
) -> tuple[ClassOccurrence, ...]:
    """Expand full-term meetings into chronological, timezone-aware occurrences.

    Match only the effective instructional weekday: an override replaces the
    physical weekday's schedule. No recurrence rules or exam events are created.
    """
    courses = tuple(courses)
    seen_indexes = set()
    for course in courses:
        if course.index in seen_indexes:
            raise SchedulingError(f"Duplicate course index: {course.index}.")
        seen_indexes.add(course.index)
        if not course.meetings:
            raise SchedulingError(f"Course {course.course_code} has no meetings.")
        if len(set(course.meetings)) != len(course.meetings):
            raise SchedulingError(f"Course {course.course_code} has duplicate meetings.")
        for meeting in course.meetings:
            if not isinstance(meeting.weekday, Weekday):
                raise SchedulingError("Meeting weekday must be a Weekday.")
            if any(clock.tzinfo is not None or clock.fold for clock in
                   (meeting.start_time, meeting.end_time)):
                raise SchedulingError("Meeting times must be naive local times with fold=0.")
            if meeting.end_time <= meeting.start_time:
                raise SchedulingError("Meeting end time must be later than its start time.")

    zone = ZoneInfo(term.timezone)
    occurrences = []
    number_of_days = (term.instruction_end - term.instruction_start).days + 1
    for offset in range(number_of_days):
        day = term.instruction_start + timedelta(days=offset)
        weekday = term.effective_instructional_day(day)
        if weekday is None:
            continue
        for course in courses:
            for meeting in course.meetings:
                if meeting.weekday == weekday:
                    occurrences.append(ClassOccurrence(
                        course=course,
                        meeting=meeting,
                        start=_local_datetime(day, meeting.start_time, zone),
                        end=_local_datetime(day, meeting.end_time, zone),
                    ))
    return tuple(sorted(occurrences, key=lambda occurrence: (
        occurrence.start, occurrence.end, occurrence.course.index,
        occurrence.meeting.location, occurrence.meeting.campus,
    )))
