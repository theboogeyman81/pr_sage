import json
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator


class ExpectedFinding(BaseModel):
    path: str
    line_range: tuple[int, int]
    category: str

    @field_validator("line_range")
    @classmethod
    def _valid_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        start, end = v
        if start < 1 or end < 1:
            raise ValueError("line_range values must be >= 1")
        if start > end:
            raise ValueError("line_range start must be <= end")
        return v


class EvalExample(BaseModel):
    diff: str
    context: str
    expected_findings: list[ExpectedFinding]
    notes: str = ""


class EvalDatasetError(Exception):
    """Raised when a JSONL line fails to parse or validate, with line number."""


def load_dataset(path: Path) -> list[EvalExample]:
    examples = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvalDatasetError(f"Line {lineno}: invalid JSON: {exc}") from exc
        try:
            examples.append(EvalExample.model_validate(data))
        except ValidationError as exc:
            raise EvalDatasetError(f"Line {lineno}: schema error: {exc}") from exc
    return examples
