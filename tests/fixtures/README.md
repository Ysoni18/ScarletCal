# Fixture provenance

- `webreg_registered_courses.txt`: original real four-course WebReg sample.
- `webreg_synthetic_friday.txt`: invented course and identifiers for regression
  testing Friday substitution and noon times. This is not a real WebReg capture.

Additional real formats still need anonymized, user-provided captures. Remove
names, student identifiers, account details, and unrelated page content before
adding a fixture. Synthetic cases do not establish support for unseen formats.

- `webreg_pass_fail.txt`: five-course schedule supplied by the user on September
  21, 2026, including THE BUSN OF EVRTHING with a pass/fail marker. Stored as
  plain clipboard text: map links use their visible building-room labels,
  italicized P is represented as `(P)`, and spaces are non-breaking spaces to
  exercise browser-copy whitespace. Tests also cover the literal `(*P*)` form.
