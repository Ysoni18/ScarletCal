from scarletcal.parser.webreg import parse_course_header


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
