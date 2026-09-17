"""HTTP transport for the existing parser → calendar → occurrences → ICS pipeline."""

import argparse
import logging
import os
from importlib.resources import files
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from scarletcal.academic_calendar import CalendarDataError, load_rutgers_term
from scarletcal.ics import ICSGenerationError, generate_ics
from scarletcal.parser.webreg import WebRegParseError, parse_webreg_schedule
from scarletcal.scheduling import SchedulingError, generate_occurrences
from scarletcal.web.security import RequestGuard


STATIC = files('scarletcal.web').joinpath('static')
app = FastAPI(title='ScarletCal', version='0.1.0')
app.add_middleware(RequestGuard)
# Explicit origins only; CORS does not authenticate callers or prevent abuse.
origins = [value.strip() for value in os.environ.get('SCARLETCAL_ALLOWED_ORIGINS', '').split(',') if value.strip()]
if '*' in origins:
    raise ValueError('Configure explicit allowed origins, not a wildcard.')
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'],
                       expose_headers=['X-Event-Count', 'X-Course-Count', 'X-Request-ID'])


class CalendarRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schedule: str = Field(min_length=1, max_length=30_000)
    term: str = Field(pattern=r'^(fall|spring)-[0-9]{4}$')
    standard_calendar: Literal[True]

    @field_validator('standard_calendar', mode='before')
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True:
            raise ValueError('Explicit standard-calendar confirmation is required.')
        return value


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    # Default validation errors can echo the entire pasted schedule. Keep them small.
    return JSONResponse(status_code=422, content={
        'detail': 'Provide schedule text (1–30,000 characters), a supported term, '
                  'and confirmation that your courses use the standard full-term calendar.'
    })


@app.get('/', include_in_schema=False)
def index():
    return Response(STATIC.joinpath('index.html').read_bytes(), media_type='text/html')


@app.get('/healthz', include_in_schema=False)
def health():
    # Check packaged term data as well as process responsiveness.
    if not terms():
        raise RuntimeError('No supported terms installed')
    return {'status': 'ok'}


@app.get('/api/terms')
def terms():
    directory = files('scarletcal').joinpath('data', 'rutgers', 'new_brunswick')
    result = []
    for resource in directory.iterdir():
        if resource.name.endswith('.json'):
            term = load_rutgers_term(resource.name.removesuffix('.json').replace('_', '-'))
            result.append({
                'id': term.term, 'label': term.term.replace('-', ' ').title(),
                'instruction_start': term.instruction_start.isoformat(),
                'instruction_end': term.instruction_end.isoformat(),
                'source': term.source,
            })
    return sorted(result, key=lambda term: term['instruction_start'])


@app.post('/api/calendar', response_class=Response, responses={
    200: {'content': {'text/calendar': {}}, 'description': 'Downloadable calendar'},
    422: {'description': 'Invalid or unsupported schedule or term'},
})
def calendar(payload: CalendarRequest):
    try:
        courses = parse_webreg_schedule(payload.schedule)
        term = load_rutgers_term(payload.term)
        occurrences = generate_occurrences(courses, term)
        content = generate_ics(occurrences, timezone=term.timezone)
    except (WebRegParseError, CalendarDataError, SchedulingError, ICSGenerationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(content, media_type='text/calendar; charset=utf-8', headers={
        'Content-Disposition': f'attachment; filename="scarletcal-{term.term}.ics"',
        'X-Event-Count': str(len(occurrences)),
        'X-Course-Count': str(len(courses)),
    })


app.mount('/static', StaticFiles(directory=str(STATIC)), name='static')


def main() -> None:
    """Run a local server; deployments can import scarletcal.web.app:app directly."""
    import uvicorn

    parser = argparse.ArgumentParser(description='Run the ScarletCal web app locally.')
    parser.add_argument('--host', default=os.environ.get('HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8000')))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, limit_concurrency=32, timeout_keep_alive=5)
