from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    path: str      # original input dict key — never a temp path
    line: int      # 1-indexed
    col: int       # 1-indexed
    rule: str      # e.g. "F401" (ruff) or "return-value" (mypy)
    message: str
    severity: str = "error"   # "error" | "warning" | "note"


class RuffError(Exception):
    """Raised when ruff exits with code ≥ 2 or cannot be found."""


class MypyError(Exception):
    """Raised when mypy exits with code ≥ 2 (fatal error, bad options, etc.)."""
