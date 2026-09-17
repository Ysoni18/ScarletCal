# Web API and frontend (Phases 7 and 8)

## Run locally

```bash
source .venv/bin/activate
python -m pip install '.[web,dev]'
scarletcal-web
```

Open http://127.0.0.1:8000. Use `--port 8001` if 8000 is busy. The server binds to
localhost by default. Reinstall after changes when using a regular installation.
For development directly from source:

```bash
python -m uvicorn scarletcal.web.app:app --app-dir src --reload
```

## API

- `GET /api/terms`: identifiers, labels, instruction dates, and source links from
  the bundled term files. No semester dates are duplicated in the frontend.
- `POST /api/calendar`: JSON containing `schedule`, `term`, and
  `standard_calendar: true`. Returns ICS bytes as an attachment, with
  `X-Event-Count` and `X-Course-Count` headers.
- `GET /healthz`: process and bundled-term health.
- `/docs`: generated API documentation.

Pasted schedules are limited to 30,000 characters. Invalid input returns 422 with
a `detail` message. Parser errors retain line numbers. Request-validation errors
avoid echoing the entire input. Responses use `Cache-Control: no-store`.

The API calls the existing parser, term loader, scheduler, and ICS exporter. It
never writes the user's schedule or generated calendar to disk. The browser
receives the download and keeps the pasted text only in the current page; it does
not use localStorage or send analytics. The production entry point logs only request IDs, route templates, status and
duration. Operators must also avoid capturing bodies in hosting infrastructure.

## Frontend

Plain HTML/CSS/JavaScript is served from the same process and packaged with the
Python distribution. No Node build step is needed locally. The Pages build generates `config.js`
with an HTTPS API origin; Render explicitly permits the Pages origin via CORS. The page has visible labels, native validation, keyboard focus styling,
a live status region, loading/error states, and a reusable download link.

The form fetches supported terms, provides the real sample as an optional example,
and submits schedule text to the API. It contains no parsing, academic calendar,
or event-generation logic. Input is rendered as text, never inserted as HTML.
The standard-calendar confirmation makes the engine's current scope explicit.
A successful response creates a browser Blob download; changing inputs removes
the previous download link so users don't accidentally save an outdated result.

## Tests and scope

Run `python -m pytest` in the environment with `web` and `dev` extras installed.
API tests cover both terms, the real 140-event pipeline, invalid requests, parser
errors, downloadable headers, static files, and absence of output files on disk.

Phase 9 adds CI configuration, a 200,000-byte request limit, private operational
logs, generic unexpected errors and deployment files. See [deployment status](deployment.md)
for remaining launch and verification steps. Parser limitations still apply.
