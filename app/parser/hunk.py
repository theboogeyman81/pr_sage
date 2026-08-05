from app.parser.diff import Hunk
from app.parser.python import Symbol


def symbols_touched(hunk: Hunk, symbols: list[Symbol]) -> list[Symbol]:
    hunk_start = hunk.new_range.start
    hunk_end = hunk.new_range.start + hunk.new_range.count - 1
    if hunk_end < hunk_start:  # count == 0: pure deletion, no new lines
        return []
    return [
        s for s in symbols
        if s.start_line <= hunk_end and s.end_line >= hunk_start
    ]
