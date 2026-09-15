from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from icalendar import Calendar
import pytest

from scarletcal.academic_calendar import load_rutgers_term
from scarletcal.ics import ICSGenerationError, generate_ics
from scarletcal.parser.webreg import parse_webreg_schedule
from scarletcal.scheduling import generate_occurrences


STAMP = datetime(2026, 9, 15, 12, tzinfo=UTC)


@pytest.fixture
def occurrences():
    text = (Path(__file__).parents[1] / 'fixtures/webreg_registered_courses.txt').read_text()
    return generate_occurrences(parse_webreg_schedule(text), load_rutgers_term('fall-2026'))


def test_full_calendar_roundtrip(occurrences):
    raw = generate_ics(occurrences, created_at=STAMP)
    calendar = Calendar.from_ical(raw)
    events = calendar.walk('VEVENT')
    assert len(events) == 140
    assert str(calendar['VERSION']) == '2.0'
    assert calendar['PRODID']
    assert len({str(e['UID']) for e in events}) == 140
    expected = {(o.start, o.end, o.course.title, f'{o.meeting.location} ({o.meeting.campus})') for o in occurrences}
    actual = {(e.decoded('DTSTART'), e.decoded('DTEND'), str(e['SUMMARY']), str(e['LOCATION'])) for e in events}
    assert actual == expected
    assert all(e.decoded('DTSTAMP') == STAMP for e in events)
    assert all(e['DTSTART'].params['TZID'] == 'America/New_York' for e in events)
    assert all(e['DTEND'].params['TZID'] == 'America/New_York' for e in events)
    assert all('RRULE' not in e for e in events)
    assert all(not component.errors for component in calendar.walk())
    assert b'\n' not in raw.replace(b'\r\n', b'')
    assert raw.endswith(b'END:VCALENDAR\r\n')


def test_embedded_timezone_and_dst(occurrences):
    raw = generate_ics(occurrences, created_at=STAMP)
    calendar = Calendar.from_ical(raw)
    zones = calendar.walk('VTIMEZONE')
    assert len(zones) == 1
    assert str(zones[0]['TZID']) == 'America/New_York'
    # Reconstruct from the embedded rules rather than the system zoneinfo database.
    zone = zones[0].to_tz(lookup_tzid=False)
    assert datetime(2026, 10, 26, 10, tzinfo=zone).utcoffset() == timedelta(hours=-4)
    assert datetime(2026, 11, 2, 10, tzinfo=zone).utcoffset() == timedelta(hours=-5)
    assert raw.index(b'BEGIN:VTIMEZONE') < raw.index(b'BEGIN:VEVENT')


def test_stable_uids_independent_of_export_time_and_input_order(occurrences):
    first = Calendar.from_ical(generate_ics(occurrences, created_at=STAMP))
    later = Calendar.from_ical(generate_ics(reversed(occurrences), created_at=STAMP + timedelta(days=1)))
    assert [str(e['UID']) for e in first.walk('VEVENT')] == [str(e['UID']) for e in later.walk('VEVENT')]


def test_text_escaping_unicode_and_folding(occurrences):
    title = 'Physics, lab; \\ textbook\nBEGIN:VEVENT\n' + '研究🔬' * 50
    original = occurrences[0]
    occurrence = replace(original, course=replace(original.course, title=title))
    raw = generate_ics([occurrence], created_at=STAMP)
    events = Calendar.from_ical(raw).walk('VEVENT')
    assert len(events) == 1
    assert str(events[0]['SUMMARY']) == title
    assert '\nSection:' in str(events[0]['DESCRIPTION'])
    assert max(len(line) for line in raw.split(b'\r\n')) <= 75
    for line in raw.split(b'\r\n'):
        line.decode('utf-8')  # No multibyte character split at a fold.


@pytest.mark.parametrize('change', ['naive', 'equal', 'reversed', 'microseconds', 'ambiguous', 'nonexistent'])
def test_invalid_occurrences(occurrences, change):
    occurrence = occurrences[0]
    if change == 'naive':
        occurrence = replace(occurrence, start=occurrence.start.replace(tzinfo=None))
    elif change == 'equal':
        occurrence = replace(occurrence, end=occurrence.start)
    elif change == 'reversed':
        occurrence = replace(occurrence, end=occurrence.start - timedelta(hours=1))
    elif change == 'microseconds':
        occurrence = replace(occurrence, start=occurrence.start.replace(microsecond=1))
    else:
        from zoneinfo import ZoneInfo
        start = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo('America/New_York')) if change == 'ambiguous' else datetime(2027, 3, 14, 2, 30, tzinfo=ZoneInfo('America/New_York'))
        occurrence = replace(occurrence, start=start, end=start + timedelta(hours=2))
    with pytest.raises(ICSGenerationError):
        generate_ics([occurrence], created_at=STAMP)


def test_duplicate_occurrences(occurrences):
    with pytest.raises(ICSGenerationError, match='Duplicate'):
        generate_ics([occurrences[0], occurrences[0]])


def test_invalid_text_control_character(occurrences):
    original = occurrences[0]
    occurrence = replace(original, course=replace(original.course, title='Physics\x00'))
    with pytest.raises(ICSGenerationError, match='control character'):
        generate_ics([occurrence])


def test_no_occurrences():
    with pytest.raises(ICSGenerationError, match='No class occurrences'):
        generate_ics([])


def test_naive_stamp(occurrences):
    with pytest.raises(ICSGenerationError, match='timezone-aware'):
        generate_ics(occurrences, created_at=STAMP.replace(tzinfo=None))
