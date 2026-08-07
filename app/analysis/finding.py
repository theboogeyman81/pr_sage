from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    path: str      # original input dict key — never a temp path
    line: int      # 1-indexed
    col: int       # 1-indexed
    rule: str      # e.g. "F401", "E501"
    message: str


class RuffError(Exception):
    """Raised when ruff exits with code ≥ 2 or cannot be found."""
