from pathlib import Path

from fastapi.testclient import TestClient
from icalendar import Calendar
import pytest

from scarletcal.web.app import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def payload():
    return {
        'schedule': (Path(__file__).parents[1] / 'fixtures/webreg_registered_courses.txt').read_text(),
        'term': 'fall-2026', 'standard_calendar': True,
    }


def test_terms_use_bundled_calendar_data(client):
    response = client.get('/api/terms')
    assert response.status_code == 200
    assert [(t['id'], t['instruction_start'], t['instruction_end']) for t in response.json()] == [
        ('fall-2026', '2026-09-01', '2026-12-10'),
        ('spring-2027', '2027-01-19', '2027-05-03'),
    ]


def test_full_pipeline_download(client, payload, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = client.post('/api/calendar', json=payload)
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/calendar')
    assert response.headers['content-disposition'] == 'attachment; filename="scarletcal-fall-2026.ics"'
    assert response.headers['x-event-count'] == '140'
    assert response.headers['x-course-count'] == '4'
    assert response.headers['cache-control'] == 'no-store'
    events = Calendar.from_ical(response.content).walk('VEVENT')
    assert len(events) == 140
    special = [e for e in events if e.decoded('DTSTART').date().isoformat() == '2026-09-08']
    assert {str(e['SUMMARY']) for e in special} == {'ANALYTICAL PHYSICS I', 'INTRO LINEAR ALGEBRA'}
    assert not list(tmp_path.iterdir())


def test_spring_download(client, payload):
    payload['term'] = 'spring-2027'
    response = client.post('/api/calendar', json=payload)
    assert response.status_code == 200
    events = Calendar.from_ical(response.content).walk('VEVENT')
    assert max(e.decoded('DTSTART').date().isoformat() for e in events) == '2027-05-03'


@pytest.mark.parametrize('key,value', [
    ('schedule', ''), ('schedule', ' '), ('schedule', 'x' * 30_001),
    ('schedule', None), ('term', 'fall-2099'), ('term', '../fall-2026'),
    ('standard_calendar', False), ('standard_calendar', 'true'),
    ('standard_calendar', 1), ('unknown', 'value'),
])
def test_invalid_request(client, payload, key, value):
    payload[key] = value
    response = client.post('/api/calendar', json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()['detail'], str)
    assert 'content-disposition' not in response.headers
    assert response.headers['cache-control'] == 'no-store'


def test_missing_confirmation(client, payload):
    del payload['standard_calendar']
    assert client.post('/api/calendar', json=payload).status_code == 422


def test_parse_error_has_line_number(client, payload):
    payload['schedule'] += '\nUnknown meeting format'
    response = client.post('/api/calendar', json=payload)
    assert response.status_code == 422
    assert 'Line ' in response.json()['detail']


def test_invalid_json_does_not_echo_input(client):
    response = client.post('/api/calendar', content='{"schedule": "private incomplete text', headers={'Content-Type':'application/json'})
    assert response.status_code == 422
    assert 'private incomplete text' not in response.text


def test_page_and_packaged_assets(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Build your class calendar' in response.text
    for name, media in [('app.js', 'javascript'), ('style.css', 'text/css'), ('example.txt', 'text/plain')]:
        response = client.get('/static/' + name)
        assert response.status_code == 200
        assert media in response.headers['content-type']
    assert client.get('/static/missing.css').status_code == 404
