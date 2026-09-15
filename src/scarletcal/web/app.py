"""HTTP transport for the existing parser → calendar → occurrences → ICS pipeline."""

import argparse
from importlib.resources import files
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from scarletcal.academic_calendar import CalendarDataError, load_rutgers_term
from scarletcal.ics import ICSGenerationError, generate_ics
from scarletcal.parser.webreg import WebRegParseError, parse_webreg_schedule
from scarletcal.scheduling import SchedulingError, generate_occurrences


STATIC = files('scarletcal.web').joinpath('static')
app = FastAPI(title='ScarletCal', version='0.1.0')


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


@app.middleware('http')
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


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
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
