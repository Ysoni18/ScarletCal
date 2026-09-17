import asyncio
import importlib
import logging

from fastapi.testclient import TestClient
import pytest

from scarletcal.web.app import app
from scarletcal.web.security import RequestGuard


def test_health_and_security_headers():
    response = TestClient(app).get('/healthz')
    assert response.json() == {'status': 'ok'}
    assert response.headers['x-frame-options'] == 'DENY'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert len(response.headers['x-request-id']) == 32


def test_declared_oversized_body_is_rejected():
    response = TestClient(app).post('/api/calendar', content='x' * 200_001)
    assert response.status_code == 413
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('headers', [[], [(b'content-length', b'1')]])
def test_streamed_body_limit_cannot_be_bypassed(headers):
    messages = iter([
        {'type': 'http.request', 'body': b'123', 'more_body': True},
        {'type': 'http.request', 'body': b'456', 'more_body': False},
    ])
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    async def must_not_run(*args):
        pytest.fail('Oversized body reached application')

    asyncio.run(RequestGuard(must_not_run, max_body_bytes=5)(
        {'type': 'http', 'path': '/api/calendar', 'headers': headers}, receive, send))
    assert sent[0]['status'] == 413


def test_unexpected_errors_and_logs_do_not_expose_private_text(monkeypatch, caplog):
    module = importlib.import_module('scarletcal.web.app')

    def fail(_):
        raise RuntimeError('PRIVATE_SCHEDULE')

    monkeypatch.setattr(module, 'parse_webreg_schedule', fail)
    with caplog.at_level(logging.INFO, logger='scarletcal.web'):
        response = TestClient(app).post('/api/calendar?secret=PRIVATE_QUERY', json={
            'schedule': 'PRIVATE_SCHEDULE', 'term': 'fall-2026', 'standard_calendar': True,
        })
    assert response.status_code == 500
    assert response.json()['request_id'] == response.headers['x-request-id']
    assert 'PRIVATE_SCHEDULE' not in response.text + caplog.text
    # Other libraries (httpx) may log URLs. Check this application's records only.
    own_logs = ' '.join(r.getMessage() for r in caplog.records if r.name == 'scarletcal.web')
    assert 'PRIVATE_QUERY' not in own_logs


def test_pages_build_preserves_design_and_project_relative_assets(tmp_path):
    from scripts.build_pages import build
    build(tmp_path, 'https://api.example.com')
    html = (tmp_path / 'index.html').read_text()
    assert 'href="./static/style.css"' in html
    assert 'src="./static/config.js"' in html
    assert 'Give your classes a place to land.' in html
    assert 'https://api.example.com' in (tmp_path / 'static/config.js').read_text()
    assert (tmp_path / 'static/style.css').stat().st_size > 1000


@pytest.mark.parametrize('origin', ['', 'http://example.com', 'https://example.com/path', 'https://user:pass@example.com'])
def test_pages_build_rejects_invalid_backend(origin, tmp_path):
    from scripts.build_pages import build
    with pytest.raises(ValueError):
        build(tmp_path, origin)


def test_cross_origin_download_headers_and_errors(monkeypatch):
    from starlette.middleware.cors import CORSMiddleware
    frontend = 'https://ysoni18.github.io'
    client = TestClient(CORSMiddleware(app, allow_origins=[frontend],
                        allow_methods=['GET', 'POST'], allow_headers=['Content-Type'],
                        expose_headers=['X-Event-Count', 'X-Course-Count', 'X-Request-ID']))
    preflight = client.options('/api/calendar', headers={
        'Origin': frontend, 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    })
    assert preflight.status_code == 200
    assert preflight.headers['access-control-allow-origin'] == frontend
    response = client.post('/api/calendar', headers={'Origin': frontend}, content='x' * 200_001)
    assert response.status_code == 413
    assert response.headers['access-control-allow-origin'] == frontend
    assert 'X-Event-Count' in response.headers['access-control-expose-headers']
    assert 'access-control-allow-origin' not in client.get('/api/terms', headers={
        'Origin': 'https://untrusted.example',
    }).headers
