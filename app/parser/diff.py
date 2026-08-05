import re
from dataclasses import dataclass, field

_HUNK_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


@dataclass
class Range:
    start: int
    count: int


@dataclass
class Hunk:
    old_range: Range
    new_range: Range
    lines: list[str] = field(default_factory=list)


@dataclass
class FileDiff:
    path: str
    hunks: list[Hunk] = field(default_factory=list)


def parse_diff(raw: str) -> list[FileDiff]:
    result: list[FileDiff] = []
    for section in re.split(r'(?=^diff --git )', raw, flags=re.MULTILINE):
        if not section.startswith('diff --git '):
            continue
        fd = _parse_section(section)
        if fd is not None:
            result.append(fd)
    return result


def _parse_section(section: str) -> FileDiff | None:
    lines = section.splitlines()

    if any('Binary files' in l for l in lines):
        return None
    if any(l.startswith('rename from') for l in lines):
        return None

    path: str | None = None
    old_path: str | None = None
    for line in lines:
        if line.startswith('--- a/'):
            old_path = line[6:]
        elif line.startswith('+++ b/'):
            path = line[6:]
            break
    if path is None:
        path = old_path  # deleted file: +++ /dev/null
    if path is None:
        return None

    fd = FileDiff(path=path)
    current: Hunk | None = None
    for line in lines:
        m = _HUNK_RE.match(line)
        if m:
            current = Hunk(
                old_range=Range(int(m.group(1)), int(m.group(2) or 1)),
                new_range=Range(int(m.group(3)), int(m.group(4) or 1)),
            )
            fd.hunks.append(current)
        elif current is not None and line and line[0] in ('+', '-', ' '):
            current.lines.append(line)

    return fd if fd.hunks else None
