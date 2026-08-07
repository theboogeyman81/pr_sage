from app.analysis.finding import Finding
from app.parser.diff import FileDiff


def aggregate(findings: list[Finding], diff: list[FileDiff]) -> list[Finding]:
    added = _added_lines(diff)
    return [f for f in findings if f.line in added.get(f.path, set())]


def _added_lines(diff: list[FileDiff]) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    for fd in diff:
        lines: set[int] = set()
        for hunk in fd.hunks:
            new_lineno = hunk.new_range.start
            for line in hunk.lines:
                if line.startswith("+"):
                    lines.add(new_lineno)
                    new_lineno += 1
                elif line.startswith(" "):
                    new_lineno += 1
                # "-" lines: do not advance new_lineno
        result[fd.path] = lines
    return result
