# Phase 9 verification — September 15, 2026

## Passed locally

- Python 3.14: 166 tests passed. Two upstream TestClient deprecation warnings
  remain; neither is suppressed.
- JavaScript syntax check (`node --check`).
- Source distribution and wheel built successfully. Installed wheel checked
  outside the repository: health, four terms, CSS, JavaScript, configuration and
  example assets present.
- In-app browser on localhost: terms loaded, example loaded, confirmation and
  generation produced success with 140 events across four courses.
- Invalid input returned a line-numbered error, preserved the input and removed
  the previous download link.
- Mobile 390 × 844 viewport: stylesheet loaded, page width did not exceed viewport;
  controls and feedback remained visible. Viewport override reset afterward.
- Keyboard: first Tab exposed “Skip to main content”; Enter moved focus to main.
- Four semester choices appeared after adding the two new calendar data files.

The Pages builder is covered by tests for relative stylesheet/config paths,
backend configuration, preserved heading and rejection of invalid origins.
API tests cover allowed/disallowed origins and preflight response headers.

## Not yet verified

- GitHub-hosted CI across Python 3.12/3.13/3.14 (workflow prepared, not pushed).
- Live Pages → Render cross-origin download and provider configuration.
- Independent Firefox/Safari runs, screen-reader testing and a full accessibility audit.
- Apple Calendar and Outlook import behavior.
- Additional real WebReg formats (new Friday fixture is synthetic).

The new Fall 2027 and Spring 2028 dates were checked against the
[official Rutgers calendar](https://scheduling.rutgers.edu/academic-calendar/).
Tests cover term boundaries, Labor Day, both Fall 2027 class-day substitutions,
the entire Thanksgiving recess and the entire Spring 2028 recess.
