from pathlib import Path

from app.parser.python import parse_python

SOURCE = (Path(__file__).parent / "fixtures" / "sample.py").read_text()
SYMBOLS = parse_python(SOURCE)
NAMES = {s.name: s for s in SYMBOLS}


def test_finds_all_symbols():
    assert set(NAMES) == {
        "top_function", "MyClass", "method_one",
        "method_two", "static_method", "decorated_function",
    }


def test_top_function_kind_and_lines():
    s = NAMES["top_function"]
    assert s.kind == "function"
    assert s.start_line == 1
    assert s.end_line == 2


def test_myclass_kind_and_lines():
    s = NAMES["MyClass"]
    assert s.kind == "class"
    assert s.start_line == 5
    assert s.end_line == 14


def test_method_kinds():
    assert NAMES["method_one"].kind == "function"
    assert NAMES["method_two"].kind == "function"
    assert NAMES["static_method"].kind == "function"


def test_decorated_function_start_line():
    s = NAMES["decorated_function"]
    assert s.kind == "function"
    assert s.start_line == 17
    assert s.end_line == 19
