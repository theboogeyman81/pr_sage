from app.parser.diff import Hunk, Range
from app.parser.python import Symbol
from app.parser.hunk import symbols_touched

TOP_FUNC   = Symbol(name="top_func",   kind="function", start_line=1,  end_line=5)
MID_CLASS  = Symbol(name="mid_class",  kind="class",    start_line=7,  end_line=20)
METHOD_ONE = Symbol(name="method_one", kind="function", start_line=9,  end_line=13)
METHOD_TWO = Symbol(name="method_two", kind="function", start_line=15, end_line=19)
BOT_FUNC   = Symbol(name="bot_func",   kind="function", start_line=22, end_line=25)

SYMBOLS = [TOP_FUNC, MID_CLASS, METHOD_ONE, METHOD_TWO, BOT_FUNC]


def _hunk(new_start: int, new_count: int) -> Hunk:
    return Hunk(old_range=Range(1, 1), new_range=Range(new_start, new_count))


def test_inside_one_symbol():
    assert symbols_touched(_hunk(2, 2), SYMBOLS) == [TOP_FUNC]


def test_crossing_two_symbols():
    assert symbols_touched(_hunk(4, 5), SYMBOLS) == [TOP_FUNC, MID_CLASS]


def test_at_boundary():
    assert symbols_touched(_hunk(5, 1), SYMBOLS) == [TOP_FUNC]


def test_outside_all_symbols():
    assert symbols_touched(_hunk(6, 1), SYMBOLS) == []


def test_inside_method_of_class():
    assert symbols_touched(_hunk(10, 2), SYMBOLS) == [MID_CLASS, METHOD_ONE]


def test_pure_deletion_hunk():
    assert symbols_touched(_hunk(5, 0), SYMBOLS) == []
