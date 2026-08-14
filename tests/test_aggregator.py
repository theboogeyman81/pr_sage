from app.analysis.aggregator import aggregate
from app.analysis.finding import Finding
from app.parser.diff import FileDiff, Hunk, Range

# Fixture diff: app/foo.py, one hunk
# @@ -10,4 +10,6 @@
#  context_before   → new line 10
# -removed_line     → not in new file
# +added_line_1     → new line 11
# +added_line_2     → new line 12
#  context_after    → new line 13
_HUNK = Hunk(
    old_range=Range(10, 4),
    new_range=Range(10, 6),
    lines=[" context_before", "-removed_line", "+added_line_1", "+added_line_2", " context_after"],
)
_DIFF = [FileDiff(path="app/foo.py", hunks=[_HUNK])]


def _finding(path: str = "app/foo.py", line: int = 11) -> Finding:
    return Finding(path=path, line=line, col=1, rule="F401", message="unused import")


def test_finding_on_added_line_kept():
    assert aggregate([_finding(line=11)], _DIFF) == [_finding(line=11)]


def test_finding_on_context_line_dropped():
    assert aggregate([_finding(line=10)], _DIFF) == []


def test_finding_on_removed_line_dropped():
    # line 9 doesn't exist in the new file numbering at all
    assert aggregate([_finding(line=9)], _DIFF) == []


def test_finding_for_unknown_file_dropped():
    assert aggregate([_finding(path="app/other.py", line=11)], _DIFF) == []


def test_multiple_findings_mixed():
    findings = [
        _finding(line=11),           # on + line → keep
        _finding(line=10),           # context → drop
        _finding(path="app/other.py", line=11),  # unknown file → drop
    ]
    assert aggregate(findings, _DIFF) == [_finding(line=11)]


def test_empty_findings_returns_empty():
    assert aggregate([], _DIFF) == []


def test_empty_diff_drops_all():
    assert aggregate([_finding(line=11)], []) == []
