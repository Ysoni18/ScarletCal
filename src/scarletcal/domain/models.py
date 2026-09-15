from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum


class Weekday(Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


@dataclass(frozen=True)
class MeetingPattern:
    weekday: Weekday
    start_time: time
    end_time: time
    location: str
    campus: str


@dataclass(frozen=True)
class Course:
    title: str
    course_code: str
    section: str
    index: str
    credits: float
    meetings: tuple[MeetingPattern, ...]


@dataclass(frozen=True)
class ClassOccurrence:
    """One actual meeting on a physical date, with timezone-aware endpoints.

    The meeting retains its normal instructional weekday; start.date() is the
    physical date, which can have a different weekday after a substitution.
    """

    course: Course
    meeting: MeetingPattern
    start: datetime
    end: datetime
