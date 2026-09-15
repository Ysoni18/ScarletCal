"""Thin command-line interface for the ScarletCal pipeline."""

import argparse
import os
from pathlib import Path
import sys
import tempfile
from zoneinfo import ZoneInfoNotFoundError

from scarletcal.academic_calendar import load_rutgers_term
from scarletcal.ics import generate_ics
from scarletcal.parser.webreg import parse_webreg_schedule
from scarletcal.scheduling import generate_occurrences


def _write_calendar(output: Path, content: bytes, force: bool) -> None:
    """Publish a complete file; preserve existing output unless force is explicit."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.scarletcal-', delete=False) as file:
            temporary = Path(file.name)
            file.write(content)
        if force:
            os.replace(temporary, output)
        else:
            # Atomic creation fails if the destination appeared while we were working.
            os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Convert pasted WebReg text to an importable class calendar.',
        epilog='Supports full-term courses on the standard New Brunswick calendar. '
               'Minicourses and school-specific calendars are not supported.',
    )
    parser.add_argument('input', type=Path, help='UTF-8 text file copied from WebReg')
    parser.add_argument('--term', required=True, help='Bundled semester: fall-2026 or spring-2027')
    parser.add_argument('-o', '--output', type=Path, default=Path('scarletcal.ics'))
    parser.add_argument('--force', action='store_true', help='Replace an existing output file')
    args = parser.parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve() or (
            args.output.exists() and args.input.samefile(args.output)
        ):
            raise ValueError('Input and output must be different files.')
        text = args.input.read_text(encoding='utf-8-sig')
        courses = parse_webreg_schedule(text)
        term = load_rutgers_term(args.term)
        occurrences = generate_occurrences(courses, term)
        content = generate_ics(occurrences, timezone=term.timezone)
        _write_calendar(args.output, content, args.force)
    except FileExistsError:
        print('scarletcal: output already exists; use --force to replace it.', file=sys.stderr)
        return 1
    except (OSError, ValueError, ZoneInfoNotFoundError) as error:
        print(f'scarletcal: {error}', file=sys.stderr)
        return 1
    print(f'Wrote {len(occurrences)} class events to {args.output}')
    return 0
