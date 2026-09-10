from dataclasses import dataclass
from datetime import time
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