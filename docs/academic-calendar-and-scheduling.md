# Academic calendars and occurrences (Phases 3 and 4)

## Try the complete pipeline so far

From an environment where this checkout is installed (`python -m pip install -e .`):

```python
from pathlib import Path

from scarletcal.academic_calendar import load_rutgers_term
from scarletcal.parser.webreg import parse_webreg_schedule
from scarletcal.scheduling import generate_occurrences

text = Path('tests/fixtures/webreg_registered_courses.txt').read_text()
courses = parse_webreg_schedule(text)
term = load_rutgers_term('fall-2026')
occurrences = generate_occurrences(courses, term)

print(len(occurrences))  # 140 for this fixture and term
for occurrence in occurrences[:3]:
    print(occurrence.course.title, occurrence.start, occurrence.end)
```

Each immutable `ClassOccurrence` carries the source
`Course`, the specific `MeetingPattern`, and timezone-aware `start` and `end`
datetimes. It retains the location and course identifiers for the
[ICS exporter and CLI](ics-and-cli.md).

## Phase 3: one physical date, one instructional weekday

`AcademicTerm.effective_instructional_day(date)` returns `Weekday` or `None`:

1. Outside the inclusive instruction start/end dates: `None`.
2. An explicit override: its weekday, or `None` for no classes.
3. Otherwise: the date's physical weekday.

For example, a physical Tuesday assigned Monday's schedule returns
`Weekday.MONDAY`. It does not also return Tuesday. Weekends are not automatically
removed: a real Saturday meeting should still occur unless a break overrides it.

`AcademicTerm` and `InstructionalOverride` are frozen dataclasses. The term copies
its overrides into a tuple. Conflicting/duplicate dates, dates outside the term,
reversed term boundaries, missing reasons, and invalid timezones fail validation.

## Calendar data and provenance

Bundled files live under `src/scarletcal/data/rutgers/new_brunswick/` and are
included in installed packages. Each records a source URL and verification date.

The `fall-2026` and `spring-2027` files were checked on September 15, 2026 against
[Rutgers Academic Scheduling's official calendar](https://scheduling.rutgers.edu/academic-calendar/).
Fall includes Labor Day, both class-day substitutions, and Thanksgiving recess;
spring includes the entire spring recess. Instruction ends at the published
regular-classes end date, so reading days and exams are excluded by the boundary.

These data cover **full-term courses following the standard New Brunswick
calendar**. Rutgers notes that some schools use different calendars. Minicourses,
school-specific dates, and emergency closures are not modeled. The pasted course
models do not identify these exceptions; callers must establish that courses use
the supported calendar before using this full-term expansion.

`load_rutgers_term('fall-2026')` selects bundled data without network access.
`load_academic_term(path)` loads an external file with the same schema. Validation
checks structure and consistency; it cannot certify that external dates are true.
Unsupported term IDs fail rather than substituting another term.

The JSON schema requires `term`, `campus`, `instruction_start`, `instruction_end`,
`timezone`, `source`, `verified_on`, and `instructional_overrides`. Each override
requires `date`, `weekday` (a full weekday name or JSON `null`), and `reason`.
Dates use `YYYY-MM-DD`. Unknown fields and duplicate JSON keys fail explicitly.

To add a term: verify its official calendar, add its JSON file, and add independent
boundary, break, and substitution assertions. Do not infer dates from other years.

## Phase 4: expand meetings against the effective day

`generate_occurrences(courses, term)` iterates through physical dates and matches
each meeting against that date's effective instructional weekday. A course's
multiple meetings on one weekday each produce a separate occurrence. Results are
returned as a tuple sorted by start, end, course index, location, and campus.

The scheduler does not parse text or hardcode Rutgers holidays. It takes the
calendar's timezone and resolves each occurrence on its actual date. This keeps
wall-clock class times constant while UTC offsets change with daylight saving.
Ambiguous or nonexistent local times fail rather than selecting an instant by guess.

Manual course models are checked for empty/duplicate meetings, duplicate course
indexes, invalid weekdays, timezone-bearing meeting times, and reversed/equal time
ranges. Overnight meetings remain unsupported. An empty course collection yields
an empty tuple. Scheduling errors return no partial result.

## Verification

Run `python -m pytest`. Tests cover both bundled calendars, all recess dates,
substitutions replacing normal weekdays, inclusive term boundaries, weekend
meetings, JSON validation, immutable calendar data, same-weekday meetings,
timezone transitions, and the real parser-to-occurrence pipeline.
