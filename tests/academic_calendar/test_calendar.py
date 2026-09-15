import json
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from importlib.resources import files

import pytest

from scarletcal.academic_calendar import (
    CalendarDataError, InstructionalOverride, load_academic_term, load_rutgers_term,
)
from scarletcal.domain.models import Weekday


@pytest.fixture
def fall():
    return load_rutgers_term('fall-2026')


@pytest.mark.parametrize('day,expected', [
    ('2026-08-31', None),
    ('2026-09-01', Weekday.TUESDAY),
    ('2026-09-05', Weekday.SATURDAY),
    ('2026-09-06', Weekday.SUNDAY),
    ('2026-09-07', None),
    ('2026-09-08', Weekday.MONDAY),
    ('2026-09-09', Weekday.WEDNESDAY),
    ('2026-11-25', Weekday.FRIDAY),
    ('2026-11-26', None),
    ('2026-11-27', None),
    ('2026-11-28', None),
    ('2026-11-29', None),
    ('2026-11-30', Weekday.MONDAY),
    ('2026-12-10', Weekday.THURSDAY),
    ('2026-12-11', None),
    ('2026-12-15', None),
])
def test_fall_instructional_dates(fall, day, expected):
    assert fall.effective_instructional_day(date.fromisoformat(day)) == expected


def test_spring_boundaries_and_entire_break():
    term = load_rutgers_term('spring-2027')
    assert term.instruction_start == date(2027, 1, 19)
    assert term.instruction_end == date(2027, 5, 3)
    assert term.effective_instructional_day(date(2027, 1, 18)) is None
    assert term.effective_instructional_day(date(2027, 1, 19)) == Weekday.TUESDAY
    assert term.effective_instructional_day(date(2027, 3, 12)) == Weekday.FRIDAY
    for day in range(13, 22):
        assert term.effective_instructional_day(date(2027, 3, day)) is None
    assert term.effective_instructional_day(date(2027, 3, 22)) == Weekday.MONDAY
    assert term.effective_instructional_day(date(2027, 5, 3)) == Weekday.MONDAY
    assert term.effective_instructional_day(date(2027, 5, 4)) is None


def test_provenance(fall):
    assert fall.source == 'https://scheduling.rutgers.edu/academic-calendar/'
    assert fall.verified_on == date(2026, 9, 15)
    assert fall.campus == 'new_brunswick'
    assert fall.timezone == 'America/New_York'


def test_term_defensively_copies_overrides(fall):
    overrides = list(fall.instructional_overrides)
    term = replace(fall, instructional_overrides=overrides)
    overrides.clear()
    assert term.effective_instructional_day(date(2026, 9, 7)) is None
    with pytest.raises(FrozenInstanceError):
        term.term = 'changed'


@pytest.mark.parametrize('changes,message', [
    ({'instruction_end': date(2026, 8, 31)}, 'Instruction end'),
    ({'instruction_start': datetime(2026, 9, 1)}, 'must be a date'),
    ({'source': ''}, 'source'),
    ({'instructional_overrides': (
        InstructionalOverride(date(2026, 8, 31), None, 'Synthetic'),
    )}, 'outside'),
])
def test_invalid_term(fall, changes, message):
    with pytest.raises(ValueError, match=message):
        replace(fall, **changes)


def test_conflicting_override_rejected(fall):
    conflict = InstructionalOverride(date(2026, 9, 7), Weekday.MONDAY, 'Synthetic')
    with pytest.raises(ValueError, match='Duplicate override'):
        replace(fall, instructional_overrides=fall.instructional_overrides + (conflict,))


def test_requires_date_not_datetime(fall):
    with pytest.raises(ValueError, match='physical calendar date'):
        fall.effective_instructional_day(datetime(2026, 9, 8))


@pytest.fixture
def calendar_data():
    return json.loads(files('scarletcal').joinpath(
        'data/rutgers/new_brunswick/fall_2026.json'
    ).read_text())


def test_external_json(tmp_path, calendar_data, fall):
    path = tmp_path / 'term.json'
    path.write_text(json.dumps(calendar_data))
    assert load_academic_term(path) == fall


@pytest.mark.parametrize('key,value', [
    ('instruction_start', '2026-02-30'),
    ('instruction_start', '20260901'),
    ('instruction_start', 20260901),
    ('instruction_end', '2025-12-10'),
    ('timezone', 'No/Such_Zone'),
    ('source', None),
    ('instructional_overrides', {}),
    ('instructional_overrides', [{'date': '2026-09-08', 'weekday': 'Mon', 'reason': 'test'}]),
    ('instructional_overrides', [{'date': '2026-09-08', 'weekday': None, 'reason': ''}]),
    ('instructional_overrides', [{'date': '2026-09-08', 'weekday': None}]),
    ('unexpected', True),
])
def test_invalid_json_fields(tmp_path, calendar_data, key, value):
    calendar_data[key] = value
    path = tmp_path / 'bad.json'
    path.write_text(json.dumps(calendar_data))
    with pytest.raises(CalendarDataError):
        load_academic_term(path)


@pytest.mark.parametrize('text', ['{', '[]', '{}', '{"term":"fall-2026","term":"spring-2027"}'])
def test_malformed_json(tmp_path, text):
    path = tmp_path / 'bad.json'
    path.write_text(text)
    with pytest.raises(CalendarDataError):
        load_academic_term(path)


@pytest.mark.parametrize('term', ['fall-2099', '../fall-2026', 'summer-2026'])
def test_unknown_term(term):
    with pytest.raises(CalendarDataError):
        load_rutgers_term(term)


def test_missing_file(tmp_path):
    with pytest.raises(CalendarDataError, match='Cannot read'):
        load_academic_term(tmp_path / 'missing.json')
