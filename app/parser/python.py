from dataclasses import dataclass

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_LANGUAGE)


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str        # "function" | "class"
    start_line: int  # 1-indexed; for decorated defs, the decorator's line
    end_line: int    # 1-indexed, inclusive


def parse_python(source: str) -> list[Symbol]:
    tree = _PARSER.parse(source.encode())
    symbols: list[Symbol] = []
    _walk(tree.root_node, symbols)
    return symbols


def _walk(node: Node, symbols: list[Symbol]) -> None:
    for child in node.children:
        if child.type == "function_definition":
            _add_symbol(child, child, symbols)
        elif child.type == "class_definition":
            _add_symbol(child, child, symbols)
            body = child.child_by_field_name("body")
            if body:
                _walk(body, symbols)
        elif child.type == "decorated_definition":
            _handle_decorated(child, symbols)


def _handle_decorated(decorated: Node, symbols: list[Symbol]) -> None:
    for child in decorated.children:
        if child.type in ("function_definition", "class_definition"):
            _add_symbol(child, decorated, symbols)
            if child.type == "class_definition":
                body = child.child_by_field_name("body")
                if body:
                    _walk(body, symbols)
            return


def _add_symbol(defn: Node, start_node: Node, symbols: list[Symbol]) -> None:
    name_node = defn.child_by_field_name("name")
    if name_node is None or name_node.text is None:
        return
    kind = "function" if defn.type == "function_definition" else "class"
    symbols.append(Symbol(
        name=name_node.text.decode(),
        kind=kind,
        start_line=start_node.start_point[0] + 1,
        end_line=defn.end_point[0] + 1,
    ))
