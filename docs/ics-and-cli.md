# ICS export and CLI (Phases 5 and 6)

## Export API

```python
from scarletcal.ics import generate_ics

content = generate_ics(occurrences, timezone='America/New_York')
# content is bytes; write with Path(...).write_bytes(content)
```

The exporter takes exact occurrences, without looking up semester rules or
parsing WebReg. It uses the [icalendar library](https://icalendar.readthedocs.io/en/stable/how-to/usage.html)
for serialization and timezone components.

Output uses VCALENDAR with VERSION and PRODID, plus one VEVENT per occurrence.
Each event has UID, UTC DTSTAMP, timezone-qualified DTSTART/DTEND, SUMMARY,
LOCATION, and a description containing course code, section, and index.
VTIMEZONE covers the event years and a year on either side. The serializer handles
UTF-8, CRLF endings, escaping, and folded content lines as specified by
[RFC 5545](https://www.rfc-editor.org/rfc/rfc5545).

UIDs use a deterministic UUID derived from course identifiers, the start/end
instants, and the location. Changing the export timestamp or event order leaves
UIDs unchanged; changing time or location creates a new UID. No attendees,
organizers, alarms, or invitation METHOD are added.

The exporter rejects empty/duplicate occurrences, naive timestamps, nonpositive
durations, subsecond precision, and nonexistent or ambiguous local times. An
optional timezone-aware `created_at` makes DTSTAMP deterministic in tests.

## CLI responsibilities

`scarletcal INPUT --term TERM [-o OUTPUT] [--force]`:

1. Read UTF-8 input, accepting a leading UTF-8 BOM.
2. Parse courses, load the bundled term, generate occurrences, and serialize.
3. Write bytes to a temporary file in the output directory.
4. Publish the completed file, refusing to replace an existing file unless forced.

No business logic is duplicated in the CLI. It returns 0 for success, 1 for
input/data/export/file errors, and argparse's 2 for invalid command syntax.
Input aliases (including symlinks and hard links) cannot be overwritten.

## Validation

Tests round-trip the complete sample, compare all 140 occurrences, verify stable
unique UIDs and Unicode folding, and reconstruct timezone offsets from the
embedded VTIMEZONE. CLI tests exercise both terms, malformed input, output
protection, path aliases, encodings, and the module entry point.

Google Calendar imported the 140-event sample successfully; see the
[interactive verification report](google-calendar-verification.md). Only a new
dedicated test calendar was created and populated. Existing events were not edited.
Apple Calendar and Outlook interactive import checks remain pending.
