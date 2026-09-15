from pathlib import Path
import os
import subprocess
import sys

from icalendar import Calendar
import pytest

from scarletcal.cli import main


FIXTURE = Path(__file__).parents[1] / 'fixtures/webreg_registered_courses.txt'


def test_default_output(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main([str(FIXTURE), '--term', 'fall-2026']) == 0
    events = Calendar.from_ical((tmp_path / 'scarletcal.ics').read_bytes()).walk('VEVENT')
    assert len(events) == 140
    assert '140 class events' in capsys.readouterr().out


def test_custom_output_and_spring_term(tmp_path):
    output = tmp_path / 'spring.ics'
    assert main([str(FIXTURE), '--term', 'spring-2027', '-o', str(output)]) == 0
    events = Calendar.from_ical(output.read_bytes()).walk('VEVENT')
    assert events
    assert min(e.decoded('DTSTART').date().isoformat() for e in events) == '2027-01-19'
    assert max(e.decoded('DTSTART').date().isoformat() for e in events) == '2027-05-03'


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'encoding', 'term'])
def test_failure_leaves_no_output(tmp_path, capsys, kind):
    source = tmp_path / 'input.txt'
    if kind == 'malformed':
        source.write_text('unknown line')
    elif kind == 'encoding':
        source.write_bytes(b'\xff\xff')
    elif kind == 'term':
        source.write_bytes(FIXTURE.read_bytes())
    output = tmp_path / 'calendar.ics'
    term = 'fall-2099' if kind == 'term' else 'fall-2026'
    assert main([str(source), '--term', term, '-o', str(output)]) == 1
    assert not output.exists()
    assert 'scarletcal:' in capsys.readouterr().err


def test_overwrite_requires_force(tmp_path, capsys):
    output = tmp_path / 'calendar.ics'
    output.write_bytes(b'original')
    args = [str(FIXTURE), '--term', 'fall-2026', '-o', str(output)]
    assert main(args) == 1
    assert output.read_bytes() == b'original'
    assert '--force' in capsys.readouterr().err
    assert main(args + ['--force']) == 0
    assert len(Calendar.from_ical(output.read_bytes()).walk('VEVENT')) == 140
    assert not list(tmp_path.glob('.scarletcal-*'))


def test_invalid_input_preserves_output_even_with_force(tmp_path):
    source = tmp_path / 'bad.txt'
    source.write_text('bad input')
    output = tmp_path / 'calendar.ics'
    output.write_bytes(b'original')
    assert main([str(source), '--term', 'fall-2026', '-o', str(output), '--force']) == 1
    assert output.read_bytes() == b'original'


@pytest.mark.parametrize('alias', ['same', 'symlink', 'hardlink'])
def test_cannot_overwrite_input(tmp_path, alias):
    source = tmp_path / 'input.txt'
    source.write_bytes(FIXTURE.read_bytes())
    output = source if alias == 'same' else tmp_path / 'output.ics'
    if alias == 'symlink':
        output.symlink_to(source)
    elif alias == 'hardlink':
        os.link(source, output)
    assert main([str(source), '--term', 'fall-2026', '-o', str(output), '--force']) == 1
    assert source.read_bytes() == FIXTURE.read_bytes()


def test_missing_output_directory(tmp_path, capsys):
    output = tmp_path / 'missing' / 'file.ics'
    assert main([str(FIXTURE), '--term', 'fall-2026', '-o', str(output)]) == 1
    assert 'scarletcal:' in capsys.readouterr().err


def test_utf8_bom(tmp_path):
    source = tmp_path / 'input.txt'
    source.write_bytes(b'\xef\xbb\xbf' + FIXTURE.read_bytes())
    assert main([str(source), '--term', 'fall-2026', '-o', str(tmp_path / 'out.ics')]) == 0


def test_missing_required_term():
    with pytest.raises(SystemExit) as error:
        main([str(FIXTURE)])
    assert error.value.code == 2


def test_module_entrypoint(tmp_path):
    result = subprocess.run([
        sys.executable, '-m', 'scarletcal', str(FIXTURE), '--term', 'fall-2026',
        '-o', str(tmp_path / 'export.ics'),
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '140 class events' in result.stdout
