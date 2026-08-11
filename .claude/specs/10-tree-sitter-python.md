# Feature 10: tree-sitter-python

## Goal
Parse a Python source string into an AST and enumerate all top-level functions, classes, and methods with their names and line ranges.

## In scope
- `app/parser/__init__.py` — empty package marker
- `app/parser/python.py` — `Symbol` dataclass + `parse_python(source: str) -> list[Symbol]`
- `tests/fixtures/sample.py` — small Python fixture file covering all symbol kinds
- `tests/test_python_parser.py` — tests over the fixture file
- `pyproject.toml` — add `tree-sitter` and `tree-sitter-python`

## Out of scope
- Cross-file resolution or imports
- Nested functions (functions inside functions)
- Type stubs or `.pyi` files
- Non-Python languages

## File structure
```
app/
  parser/
    __init__.py          # new — empty
    python.py            # new — Symbol + parse_python()
tests/
  fixtures/
    sample.py            # new — fixture source for tests
  test_python_parser.py  # new — tests
pyproject.toml           # modified — two new deps
```

## Contracts

### `app/parser/python.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str        # "function" | "class"
    start_line: int  # 1-indexed, inclusive; for decorated defs, this is the decorator line
    end_line: int    # 1-indexed, inclusive
```

```python
def parse_python(source: str) -> list[Symbol]:
    """
    Parse Python source and return all top-level functions, classes,
    and methods (functions inside class bodies).

    Symbols are returned in source order.
    Decorated definitions use the decorator's line as start_line.
    Nested functions (functions inside functions) are not returned.
    """
```

**AST walk strategy:**
- Parse `source.encode()` using a module-level `Parser` instance (created once, reused).
- Walk direct children of the `module` node for top-level symbols.
- For each `class_definition`, walk its `body` children for methods.
- Handle `decorated_definition` at both levels: start_line = decorator node's start; kind/name come from the inner `function_definition` or `class_definition`.
- Line numbers: `node.start_point[0] + 1` and `node.end_point[0] + 1` (tree-sitter rows are 0-indexed).

**Module-level parser init (inside `python.py`):**
```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_LANGUAGE)
```

Created once at import time — safe because it has no dependency on `get_settings()` or env vars.

### `tests/fixtures/sample.py`

```python
def top_function(x: int) -> int:
    return x + 1


class MyClass:
    def method_one(self) -> None:
        pass

    async def method_two(self) -> str:
        return "hello"

    @staticmethod
    def static_method() -> None:
        pass


@some_decorator
def decorated_function() -> None:
    pass
```

## Dependencies

New additions to `pyproject.toml` main deps:
```
tree-sitter==0.23.2
tree-sitter-python==0.23.2
```

Both must be the same minor version — the grammar package (`tree-sitter-python`) must be compatible with the binding (`tree-sitter`).

## Tests

All tests load the fixture file via `pathlib.Path` and call `parse_python()` once. Assertions check individual symbols by name.

```python
# tests/test_python_parser.py
from pathlib import Path
from app.parser.python import Symbol, parse_python

SOURCE = (Path(__file__).parent / "fixtures" / "sample.py").read_text()
SYMBOLS = parse_python(SOURCE)
NAMES = {s.name: s for s in SYMBOLS}
```

- `test_finds_all_symbols` — asserts the set of names equals `{"top_function", "MyClass", "method_one", "method_two", "static_method", "decorated_function"}` (exactly, no extras, no missing).
- `test_top_function_kind_and_lines` — `NAMES["top_function"].kind == "function"` · `start_line == 1` · `end_line == 2`.
- `test_myclass_kind_and_lines` — `NAMES["MyClass"].kind == "class"` · `start_line == 5` · spans at least through `static_method`.
- `test_method_kinds` — `method_one`, `method_two`, `static_method` all have `kind == "function"`.
- `test_decorated_function_start_line` — `NAMES["decorated_function"].start_line` equals the line of `@some_decorator` (not the `def` line).

## Acceptance criteria
1. All 5 tests pass.
2. `parse_python` correctly identifies top-level functions, top-level classes, and methods (inside class bodies) with accurate 1-indexed line ranges.
3. Decorated definitions: `start_line` is the decorator's line, not the `def`/`class` line.
4. Nested functions (functions inside functions) are NOT returned.
5. The module-level `_PARSER` is created once at import time with no env var dependencies.
6. All existing 18 tests remain green.
