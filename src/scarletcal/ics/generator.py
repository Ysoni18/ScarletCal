"""Serialize exact occurrences using RFC 5545 components."""

from collections.abc import Iterable
from datetime import UTC, date, datetime
import json
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Timezone

from scarletcal.domain.models import ClassOccurrence


class ICSGenerationError(ValueError):
    """Occurrences cannot be represented safely in an iCalendar file."""


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ICSGenerationError('Event times and creation timestamp must be timezone-aware.')
    if value.microsecond:
        raise ICSGenerationError('Subsecond timestamps are unsupported by this exporter.')
    if value.astimezone(UTC).astimezone(value.tzinfo) != value:
        raise ICSGenerationError('Nonexistent local event time.')


def _uid(occurrence: ClassOccurrence) -> str:
    # Export timestamp and title are deliberately excluded from event identity.
    identity = json.dumps([
        occurrence.course.course_code, occurrence.course.section, occurrence.course.index,
        occurrence.start.astimezone(UTC).isoformat(),
        occurrence.end.astimezone(UTC).isoformat(),
        occurrence.meeting.location, occurrence.meeting.campus,
    ], ensure_ascii=True, separators=(',', ':'))
    return str(uuid5(NAMESPACE_URL, 'urn:scarletcal:occurrence:' + identity)) + '@scarletcal'


def generate_ics(
    occurrences: Iterable[ClassOccurrence], *,
    timezone: str = 'America/New_York', created_at: datetime | None = None,
) -> bytes:
    """Return UTF-8 ICS bytes, with individual events and an embedded timezone.

    This exporter has no knowledge of academic terms, holidays, or WebReg text.
    An empty or invalid collection raises rather than producing an unusable file.
    """
    occurrences = tuple(occurrences)
    if not occurrences:
        raise ICSGenerationError('No class occurrences to export.')
    zone = ZoneInfo(timezone)
    stamp = created_at if created_at is not None else datetime.now(UTC).replace(microsecond=0)
    _aware(stamp)
    calendar = Calendar()
    calendar.add('prodid', '-//ScarletCal//Class Schedule//EN')
    calendar.add('version', '2.0')
    calendar.add('calscale', 'GREGORIAN')
    seen = set()
    events = []
    for occurrence in occurrences:
        for text in (occurrence.course.title, occurrence.course.course_code,
                     occurrence.course.section, occurrence.course.index,
                     occurrence.meeting.location, occurrence.meeting.campus):
            if any((ord(char) < 32 and char not in '\t\r\n') or ord(char) == 127 for char in text):
                raise ICSGenerationError('Unsupported control character in event text.')
        _aware(occurrence.start)
        _aware(occurrence.end)
        if occurrence.end.astimezone(UTC) <= occurrence.start.astimezone(UTC):
            raise ICSGenerationError('Event end must be later than its start.')
        start, end = occurrence.start.astimezone(zone), occurrence.end.astimezone(zone)
        for value in (start, end):
            if value.replace(fold=0).utcoffset() != value.replace(fold=1).utcoffset():
                raise ICSGenerationError('Ambiguous local event time cannot use a TZID safely.')
        uid = _uid(occurrence)
        if uid in seen:
            raise ICSGenerationError('Duplicate class occurrence.')
        seen.add(uid)
        event = Event()
        event.add('uid', uid)
        event.add('dtstamp', stamp.astimezone(UTC))
        event.add('dtstart', start)
        event.add('dtend', end)
        event.add('summary', occurrence.course.title)
        event.add('location', f'{occurrence.meeting.location} ({occurrence.meeting.campus})')
        event.add('description', (
            f'Course: {occurrence.course.course_code}\n'
            f'Section: {occurrence.course.section}\nIndex: {occurrence.course.index}'
        ))
        events.append((start, uid, event))

    first_year = min(o.start.astimezone(zone).year for o in occurrences)
    last_year = max(o.end.astimezone(zone).year for o in occurrences)
    if first_year == 1 or last_year == 9999:
        raise ICSGenerationError('Event years must be between 2 and 9998.')
    calendar.add_component(Timezone.from_tzinfo(
        zone, tzid=timezone,
        first_date=date(first_year - 1, 1, 1), last_date=date(last_year + 1, 12, 31),
    ))
    for _, _, event in sorted(events, key=lambda item: (item[0], item[1])):
        calendar.add_component(event)
    return calendar.to_ical()
