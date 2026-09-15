"""Parse plain-text course headers copied from Rutgers WebReg."""

import re


_COURSE_HEADER_RE = re.compile(
    r"(?P<title>\S[^\r\n]*?)\s+"
    r"\((?P<course_code>[0-9]{2}:[0-9]{3}:[0-9]{3})\)\s+"
    r"Section\s+(?P<section>[A-Za-z0-9]+)\s+\|\s+"
    r"\[(?P<index>[0-9]{5})\]\s+"
    r"Credits:\s+(?P<credits>[0-9]+\.[0-9]+)"
)


def parse_course_header(line: str) -> dict[str, str | float] | None:
    """Return header metadata, or None when the line is not a course header."""
    match = _COURSE_HEADER_RE.fullmatch(line.strip())
    if match is None:
        return None

    return {
        "title": match.group("title"),
        "course_code": match.group("course_code"),
        "section": match.group("section"),
        "index": match.group("index"),
        "credits": float(match.group("credits")),
    }
