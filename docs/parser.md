# WebReg parser (Phase 2)

```python
from scarletcal.parser.webreg import WebRegParseError, parse_webreg_schedule

try:
    courses = parse_webreg_schedule(pasted_text)
except WebRegParseError as error:
    print(error)
```

`parse_webreg_schedule()` returns a tuple of immutable `Course` objects. Each
course contains a tuple of `MeetingPattern` objects in clipboard order. Two
meetings on the same weekday remain separate.

## How it works

1. `parse_course_header()` uses a compiled regex with named groups. It returns
   metadata or `None` for a non-header. Identifiers remain strings (including
   section `02`); credits become a float. Title whitespace is normalized.
2. `parse_meeting()` recognizes a weekday, two 12-hour clock times, a location,
   and a campus. It returns structured `datetime.time` values in a
   `MeetingPattern`, or raises `WebRegParseError`.
3. The schedule parser scans lines, finishing the previous course when it finds
   a new header. It ignores blank lines and the exact observed WebReg banner.
   All other lines must parse, or the entire operation raises an error with the
   offending line number. A header without meetings reports its header line.

The single-header helper returning `None` does not mean the full parser ignores
malformed headers: those lines fail meeting parsing and produce an error.

## Supported input and limits

The fixture `tests/fixtures/webreg_registered_courses.txt` combines the actual
navigation banner and four-course plain-text sample supplied by the developer.
It contains 10 meetings, including two Thursday meetings for Computer Science.
The additional clock/error test cases are synthetic boundary cases.

Currently supported meetings have:

- A full English weekday name, Monday through Sunday.
- Explicit uppercase AM/PM on both times, with an end later than the start.
- A building-room token such as `HLL-114` or `LSH-B267`.
- The observed campus names `Busch` or `Livingston`.

Other campus/location formats, online/asynchronous courses, arranged times,
combined weekday abbreviations, and overnight meetings are unsupported and
raise errors. Add real clipboard fixtures before extending these formats.
Duplicate course indexes and identical meetings within a course also raise
errors rather than generating duplicate calendar entries. Empty input fails.

This layer does not determine semester dates, holidays, instructional weekday
substitutions, or calendar events. Those belong to later phases.

## Tests

Run `python -m pytest` from the project root. Pytest explicitly adds this
checkout's `src` directory so another installed ScarletCal checkout cannot
silently take precedence.
