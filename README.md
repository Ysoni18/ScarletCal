# ScarletCal

Convert registered Rutgers WebReg courses into a downloadable `.ics` calendar.
The CLI uses deterministic parsing and verified academic-calendar data. It runs
locally without a Rutgers login, scraping, or sending your schedule to a server.

## Install

Requires Python 3.12 or newer. Use a dedicated virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install '.[dev]'
```

On Windows, activate with `.venv\Scripts\activate` instead.

Reinstall after source changes to update the CLI. An editable install
(`python -m pip install -e '.[dev]'`) is also available for development; if Python
cannot find ScarletCal after that install, use the regular installation above.

## Generate a calendar

Copy your registered WebReg schedule into a UTF-8 file named `schedule.txt`, then:

```bash
scarletcal schedule.txt --term fall-2026
```

This creates `scarletcal.ics` in the current directory. You can also run
`python -m scarletcal` with the same arguments.

```bash
scarletcal schedule.txt --term spring-2027 -o spring.ics
scarletcal schedule.txt --term fall-2026 -o scarletcal.ics --force
scarletcal --help
```

Existing files are preserved unless `--force` is supplied. Input and output cannot
be the same file. An invalid schedule or unknown term prints an error to stderr,
returns a nonzero exit code, and leaves the output unchanged.

Try the supplied real sample:

```bash
scarletcal tests/fixtures/webreg_registered_courses.txt --term fall-2026 -o sample.ics
```

Expected: **140 class events**.

## Scope

- Standard New Brunswick calendar; full-term courses only.
- Bundled Fall 2026 and Spring 2027 calendars, with source and verification date.
- Current parser supports the observed Busch/Livingston building-room format.
- Minicourses, special school calendars, online/arranged meetings, exams,
  assignments, and emergency closures are not supported.

Each actual class meeting becomes an individual event. Events retain local
`America/New_York` times with an embedded timezone definition. There are no
recurring class-event rules to reconcile with academic-calendar exceptions.

## Import and verification status

The file is intended for calendar applications that support iCalendar imports,
including Google Calendar, Apple Calendar, and Outlook. Automated tests verify
serialization, event data, escaping, line folding, and embedded timezone rules.
**Interactive imports into those three applications have not yet been verified.**

Use a separate test calendar for the first import. Confirm the 140-event sample,
September 8's Monday classes, November 25's Friday substitution, no holiday
meetings, and class times on both sides of the daylight-saving change.

Exporting again preserves UIDs for unchanged occurrences, but file import is not
calendar synchronization. Do not assume a client will remove obsolete events or
avoid duplicates after a changed schedule; replacing the dedicated calendar is
safer than repeatedly importing changed files into your main calendar.

## Development

```bash
python -m pytest
```

Pipeline:

```text
WebReg text → Course objects → academic calendar → ClassOccurrence objects → ICS
```

The CLI only connects these layers and handles file I/O.

- [Parser design](docs/parser.md)
- [Calendar and scheduling design](docs/academic-calendar-and-scheduling.md)
- [ICS and CLI design](docs/ics-and-cli.md)
