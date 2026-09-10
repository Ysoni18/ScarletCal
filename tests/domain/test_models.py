from datetime import time

from scarletcal.domain.models import Course, MeetingPattern, Weekday


def test_create_course_with_multiple_meetings():
    course = Course(
        title="INTRO COMPUTER SCI",
        course_code="01:198:111",
        section="S4",
        index="26200",
        credits=4.0,
        meetings=(
            MeetingPattern(
                weekday=Weekday.TUESDAY,
                start_time=time(14, 0),
                end_time=time(15, 20),
                location="HLL-114",
                campus="Busch",
            ),
            MeetingPattern(
                weekday=Weekday.THURSDAY,
                start_time=time(14, 0),
                end_time=time(15, 20),
                location="HLL-114",
                campus="Busch",
            ),
        ),
    )

    assert course.course_code == "01:198:111"
    assert course.credits == 4.0
    assert len(course.meetings) == 2
    assert course.meetings[0].weekday == Weekday.TUESDAY