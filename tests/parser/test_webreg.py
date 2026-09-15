from datetime import time
from pathlib import Path

import pytest

from scarletcal.domain.models import MeetingPattern, Weekday
from scarletcal.parser.webreg import (
    WebRegParseError,
    parse_course_header,
    parse_meeting,
    parse_webreg_schedule,
)


def test_parse_course_header():
    line = "INTRO COMPUTER SCI (01:198:111) Section S4 | [26200] Credits: 4.0"

    assert parse_course_header(line) == {
        "title": "INTRO COMPUTER SCI",
        "course_code": "01:198:111",
        "section": "S4",
        "index": "26200",
        "credits": 4.0,
    }


def test_meeting_line_returns_none():
    line = "Tuesday 2:00 PM - 3:20 PM HLL-114 Busch"

    assert parse_course_header(line) is None


HEADER = "INTRO COMPUTER SCI (01:198:111) Section S4 | [26200] Credits: 4.0"
MEETING = "Tuesday 2:00 PM - 3:20 PM HLL-114 Busch"


@pytest.fixture
def real_schedule():
    return (Path(__file__).parents[1] / "fixtures" / "webreg_registered_courses.txt").read_text()


def test_parse_meeting():
    assert parse_meeting(MEETING) == MeetingPattern(
        weekday=Weekday.TUESDAY,
        start_time=time(14),
        end_time=time(15, 20),
        location="HLL-114",
        campus="Busch",
    )


@pytest.mark.parametrize("clock,end,expected", [
    ("12:00 AM", "1:00 AM", time(0)),
    ("12:10 PM", "1:30 PM", time(12, 10)),
    ("8:45 AM", "9:40 AM", time(8, 45)),
    ("8:00 PM", "9:20 PM", time(20)),
])
def test_clock_conversion(clock, end, expected):
    meeting = parse_meeting(f"Thursday {clock} - {end} BE-121 Livingston")
    assert meeting.start_time == expected


@pytest.mark.parametrize("weekday", list(Weekday))
def test_weekdays(weekday):
    assert parse_meeting(MEETING.replace("Tuesday", weekday.value)).weekday == weekday


@pytest.mark.parametrize("line", [
    "Tuesday 0:00 PM - 3:20 PM HLL-114 Busch",
    "Tuesday 13:00 PM - 3:20 PM HLL-114 Busch",
    "Tuesday 2:60 PM - 3:20 PM HLL-114 Busch",
    "Tuesday 2:00 - 3:20 PM HLL-114 Busch",
    "Tuesday 2:00 PM - 3:20 PM HLL-114",
    "Tuesday 2:00 PM - 3:20 PM HLL-114 Unknown",
    "Tuesday 2:00 PM - 3:20 PM HLL-114 Busch extra text",
    "Tuesday 2:00 PM - 3:20 PM Online",
    "Hours by Arrangement",
    "TBA",
    "Funday 2:00 PM - 3:20 PM HLL-114 Busch",
    "Tuesday\n2:00 PM - 3:20 PM HLL-114 Busch",
])
def test_invalid_or_unsupported_meeting(line):
    with pytest.raises(WebRegParseError, match="Invalid or unsupported meeting"):
        parse_meeting(line)


@pytest.mark.parametrize("start,end", [
    ("2:00 PM", "2:00 PM"),
    ("3:00 PM", "2:00 PM"),
    ("11:00 PM", "1:00 AM"),
])
def test_invalid_time_order(start, end):
    with pytest.raises(WebRegParseError, match="end time must be later"):
        parse_meeting(f"Monday {start} - {end} HLL-114 Busch")


def test_real_multi_course_schedule(real_schedule):
    courses = parse_webreg_schedule(real_schedule)
    assert isinstance(courses, tuple)
    assert [
        (c.title, c.course_code, c.section, c.index, c.credits, len(c.meetings))
        for c in courses
    ] == [
        ("INTRO COMPUTER SCI", "01:198:111", "S4", "26200", 4.0, 3),
        ("INTRO LINEAR ALGEBRA", "01:640:250", "C2", "13065", 3.0, 2),
        ("MULTIVARIABLE CALC", "01:640:251", "H5", "13113", 4.0, 3),
        ("ANALYTICAL PHYSICS I", "01:750:123", "02", "13307", 2.0, 2),
    ]
    assert all(isinstance(c.meetings, tuple) for c in courses)
    assert [
        (m.weekday, m.start_time, m.end_time, m.location, m.campus)
        for c in courses for m in c.meetings
    ] == [
        (Weekday.TUESDAY, time(14), time(15, 20), "HLL-114", "Busch"),
        (Weekday.THURSDAY, time(14), time(15, 20), "HLL-114", "Busch"),
        (Weekday.THURSDAY, time(8, 45), time(9, 40), "BE-121", "Livingston"),
        (Weekday.MONDAY, time(14), time(15, 20), "LSH-B267", "Livingston"),
        (Weekday.WEDNESDAY, time(14), time(15, 20), "LSH-B267", "Livingston"),
        (Weekday.TUESDAY, time(15, 50), time(17, 10), "SEC-210", "Busch"),
        (Weekday.THURSDAY, time(15, 50), time(17, 10), "SEC-210", "Busch"),
        (Weekday.WEDNESDAY, time(12, 10), time(13, 30), "ARC-204", "Busch"),
        (Weekday.WEDNESDAY, time(10, 20), time(11, 40), "PHY-001", "Busch"),
        (Weekday.MONDAY, time(10, 20), time(11, 40), "PAB-227", "Busch"),
    ]


def test_whitespace_and_windows_newlines(real_schedule):
    varied = "\r\n".join("\t" + line.replace(" ", "\t") + " "
                          if not line.startswith("Registered") else line
                          for line in real_schedule.splitlines())
    assert parse_webreg_schedule(varied) == parse_webreg_schedule(real_schedule)


@pytest.mark.parametrize("text", ["", " \n\t", "Registered CoursesOnline Bill Payment View / Print Schedule"])
def test_no_courses(text):
    with pytest.raises(WebRegParseError, match="No courses found"):
        parse_webreg_schedule(text)


def test_orphan_meeting():
    with pytest.raises(WebRegParseError, match="Line 2: Meeting appears before"):
        parse_webreg_schedule("\n" + MEETING)


@pytest.mark.parametrize("suffix", ["", "\n" + HEADER.replace("26200", "13065")])
def test_course_without_meetings(suffix):
    with pytest.raises(WebRegParseError, match="Line 1: Course .* has no supported timed meetings"):
        parse_webreg_schedule(HEADER + suffix)


@pytest.mark.parametrize("bad_line", [
    HEADER.replace("Credits: 4.0", "Credits: four"),
    HEADER + " unexpected",
    "Unexpected WebReg notice",
    "Tuesday 3:20 PM - 2:00 PM HLL-114 Busch",
    "Hours by Arrangement",
])
def test_bad_line_after_valid_course_is_not_ignored(bad_line):
    with pytest.raises(WebRegParseError, match="Line 3:"):
        parse_webreg_schedule(f"{HEADER}\n{MEETING}\n{bad_line}")


def test_duplicate_course():
    with pytest.raises(WebRegParseError, match="Line 3: Duplicate course index"):
        parse_webreg_schedule(f"{HEADER}\n{MEETING}\n{HEADER}\n{MEETING}")


def test_duplicate_meeting():
    with pytest.raises(WebRegParseError, match="Line 3: Duplicate meeting"):
        parse_webreg_schedule(f"{HEADER}\n{MEETING}\n{MEETING}")


def test_header_does_not_consume_multiple_lines():
    assert parse_course_header(HEADER.replace("Section", "\nSection")) is None
