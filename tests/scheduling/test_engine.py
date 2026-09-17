from dataclasses import replace
from datetime import date, time, timedelta
from pathlib import Path

import pytest

from scarletcal.academic_calendar import load_rutgers_term
from scarletcal.domain.models import Course, MeetingPattern, Weekday
from scarletcal.parser.webreg import parse_webreg_schedule
from scarletcal.scheduling import SchedulingError, generate_occurrences


def course_for(*weekdays):
    return Course('Synthetic test course', '01:000:001', '01', '00001', 3.0, tuple(
        MeetingPattern(day, time(10), time(11), 'TEST-100', 'Busch') for day in weekdays
    ))


@pytest.fixture
def fall():
    return load_rutgers_term('fall-2026')


def test_monday_schedule_replaces_tuesday(fall):
    course = course_for(Weekday.MONDAY, Weekday.TUESDAY)
    events = generate_occurrences([course], fall)
    special = [e for e in events if e.start.date() == date(2026, 9, 8)]
    assert len(special) == 1
    assert special[0].meeting.weekday == Weekday.MONDAY
    assert special[0].start.weekday() == 1
    assert special[0].course is course
    assert not any(e.start.date() == date(2026, 9, 7) for e in events)


def test_friday_schedule_replaces_wednesday(fall):
    events = generate_occurrences([course_for(Weekday.WEDNESDAY, Weekday.FRIDAY)], fall)
    special = [e for e in events if e.start.date() == date(2026, 11, 25)]
    assert len(special) == 1
    assert special[0].meeting.weekday == Weekday.FRIDAY
    assert special[0].start.weekday() == 2


def test_term_boundaries_and_thanksgiving(fall):
    events = generate_occurrences([course_for(*Weekday)], fall)
    days = {e.start.date() for e in events}
    assert min(days) == date(2026, 9, 1)
    assert max(days) == date(2026, 12, 10)
    assert len(days) == 96  # 101 inclusive dates minus Labor Day and four recess dates.
    assert all(date(2026, 11, day) not in days for day in range(26, 30))
    assert date(2026, 9, 5) in days  # Saturday meetings are not silently removed.
    assert date(2026, 9, 6) in days


def test_spring_break_suppresses_every_weekday():
    term = load_rutgers_term('spring-2027')
    events = generate_occurrences([course_for(*Weekday)], term)
    assert events[0].start.date() == date(2027, 1, 19)
    assert events[-1].start.date() == date(2027, 5, 3)
    assert not any(date(2027, 3, 13) <= e.start.date() <= date(2027, 3, 21) for e in events)


def test_real_parser_to_occurrences(fall):
    text = (Path(__file__).parents[1] / 'fixtures/webreg_registered_courses.txt').read_text()
    courses = parse_webreg_schedule(text)
    events = generate_occurrences(courses, fall)
    assert isinstance(events, tuple)
    # Each Mon/Tue/Wed/Thu pattern has 14 instructional dates in this term.
    assert len(events) == 140
    assert [sum(e.course.index == c.index for e in events) for c in courses] == [42, 28, 42, 28]
    thursday = [e for e in events if e.course.index == '26200' and e.start.date() == date(2026, 9, 3)]
    assert [e.start.time() for e in thursday] == [time(8, 45), time(14)]
    assert [e.meeting.location for e in thursday] == ['BE-121', 'HLL-114']
    assert all(e.end.date() == e.start.date() for e in events)
    assert events == generate_occurrences(reversed(courses), fall)


def test_timezone_keeps_wall_clock_across_dst(fall):
    events = generate_occurrences([course_for(Weekday.MONDAY)], fall)
    by_date = {e.start.date(): e for e in events}
    before = by_date[date(2026, 10, 26)]
    after = by_date[date(2026, 11, 2)]
    assert before.start.time() == after.start.time() == time(10)
    assert before.start.utcoffset() == timedelta(hours=-4)
    assert after.start.utcoffset() == timedelta(hours=-5)
    assert all(e.start.tzinfo.key == e.end.tzinfo.key == 'America/New_York' for e in events)


@pytest.mark.parametrize('day,start,end,message', [
    (date(2026, 11, 1), time(1, 30), time(2, 30), 'Ambiguous'),
    (date(2027, 3, 14), time(2, 30), time(3, 30), 'Nonexistent'),
    (date(2027, 3, 14), time(1, 30), time(2, 30), 'Nonexistent'),
])
def test_dst_transition_times_fail_explicitly(fall, day, start, end, message):
    term = replace(fall, term='synthetic', instruction_start=day, instruction_end=day,
                   instructional_overrides=())
    course = course_for(Weekday.SUNDAY)
    course = replace(course, meetings=(replace(course.meetings[0], start_time=start, end_time=end),))
    with pytest.raises(SchedulingError, match=message):
        generate_occurrences([course], term)


def test_empty_course_collection(fall):
    assert generate_occurrences([], fall) == ()


@pytest.mark.parametrize('kind', ['empty', 'duplicate_course', 'duplicate_meeting', 'reversed_times', 'aware_time'])
def test_invalid_manual_models(fall, kind):
    course = course_for(Weekday.MONDAY)
    if kind == 'empty':
        course = replace(course, meetings=())
    elif kind == 'duplicate_meeting':
        course = replace(course, meetings=course.meetings * 2)
    elif kind == 'reversed_times':
        course = replace(course, meetings=(replace(course.meetings[0], end_time=time(9)),))
    elif kind == 'aware_time':
        from zoneinfo import ZoneInfo
        course = replace(course, meetings=(replace(course.meetings[0], start_time=time(10, tzinfo=ZoneInfo('America/New_York'))),))
    with pytest.raises(SchedulingError):
        generate_occurrences([course] * (2 if kind == 'duplicate_course' else 1), fall)


def test_fall_2027_published_exceptions_and_boundaries():
    events = generate_occurrences([course_for(*Weekday)], load_rutgers_term('fall-2027'))
    by_date = {event.start.date(): event for event in events}
    assert min(by_date) == date(2027, 9, 1)
    assert max(by_date) == date(2027, 12, 13)
    assert date(2027, 9, 6) not in by_date
    assert by_date[date(2027, 9, 8)].meeting.weekday == Weekday.MONDAY
    assert by_date[date(2027, 11, 29)].meeting.weekday == Weekday.WEDNESDAY
    assert all(date(2027, 11, day) not in by_date for day in range(24, 29))


def test_spring_2028_published_break_and_boundaries():
    events = generate_occurrences([course_for(*Weekday)], load_rutgers_term('spring-2028'))
    days = {event.start.date() for event in events}
    assert min(days) == date(2028, 1, 18)
    assert max(days) == date(2028, 5, 1)
    assert all(date(2028, 3, day) not in days for day in range(11, 20))
