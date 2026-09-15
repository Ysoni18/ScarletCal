# Google Calendar import verification

Verified on September 15, 2026 through the Google Calendar web interface.

## Input and isolation

- Source: `sample.ics`, generated from the real four-course fixture for Fall 2026.
- Source SHA-256: `3590c71dc1eac0195f4de9083445e74fd13426bc79583a06fd385cc7f72fd8c0`.
- Destination: newly created `ScarletCal Verification — Fall 2026` calendar.
- Calendar timezone and existing display timezone: Eastern Time — New York.
- The destination was explicitly selected before import. No existing events were
  edited or deleted. The test calendar remains available for inspection.

## Observed results

| Check | Google Calendar result |
| --- | --- |
| Import count | Confirmation reported **Imported 140 out of 140 events**. |
| Destination | Imported event labels identify the dedicated ScarletCal calendar. |
| Labor Day, September 7 | No imported timed classes. The separate US holiday calendar displays Labor Day. |
| Monday substitution, September 8 | Physics 10:20–11:40am and Linear Algebra 2–3:20pm; normal Tuesday CS/Calculus meetings absent. |
| Multiple Thursday meetings | September 10 and 17 retain CS at 8:45–9:40am and 2–3:20pm, in different locations. |
| November 25 | Normal Wednesday classes absent, consistent with the Friday substitution for this sample. |
| Thanksgiving | No imported classes on November 26–28 in the inspected week. |
| DST | Physics remains 10:20–11:40am and Linear Algebra 2–3:20pm on both October 26 and November 2. |
| Last instructional day | December 10 shows both CS meetings and Calculus 3:50–5:10pm. December 11–12 have no events. |
| Event detail | December 10 morning CS displays BE-121 (Livingston), course 01:198:111, section S4, and index 26200. |

## Limits

This is one real sample imported once, followed by targeted UI spot checks, not a
comparison of every imported property against a Google export. The sample has no
Friday courses, so the November 25 check confirms Wednesday suppression but does
not positively verify a Friday meeting on that date. The sample also has no
weekend meetings. Other boundaries and positive Friday substitutions are covered
by automated scheduling tests, not by this Google import session.

Reimport/update behavior, Spring 2027, Apple Calendar, and Outlook remain outside
this interactive verification. The test calendar was retained; it was not deleted.
