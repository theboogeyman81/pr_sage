import json

import pytest

from app.eval.schema import EvalDatasetError, EvalExample, load_dataset

_VALID = {
    "diff": "diff --git a/app/foo.py b/app/foo.py\n+x = 1\n",
    "context": "x = 1",
    "expected_findings": [{"path": "app/foo.py", "line_range": [1, 2], "category": "logic-error"}],
    "notes": "test example",
}


def _write(tmp_path, lines: list[dict]) -> object:
    p = tmp_path / "data.jsonl"
    p.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    return p


def test_valid_example_parses(tmp_path):
    p = _write(tmp_path, [_VALID])
    examples = load_dataset(p)
    assert len(examples) == 1
    ex = examples[0]
    assert ex.diff == _VALID["diff"]
    assert ex.expected_findings[0].category == "logic-error"
    assert ex.expected_findings[0].line_range == (1, 2)


def test_empty_findings_valid(tmp_path):
    record = {**_VALID, "expected_findings": []}
    p = _write(tmp_path, [record])
    examples = load_dataset(p)
    assert examples[0].expected_findings == []


def test_notes_defaults_to_empty_string(tmp_path):
    record = {k: v for k, v in _VALID.items() if k != "notes"}
    p = _write(tmp_path, [record])
    assert load_dataset(p)[0].notes == ""


def test_missing_diff_raises(tmp_path):
    record = {k: v for k, v in _VALID.items() if k != "diff"}
    p = _write(tmp_path, [record])
    with pytest.raises(EvalDatasetError) as exc_info:
        load_dataset(p)
    assert "Line 1" in str(exc_info.value)


def test_invalid_line_range_raises(tmp_path):
    record = {**_VALID, "expected_findings": [{"path": "a.py", "line_range": [5, 3], "category": "x"}]}
    p = _write(tmp_path, [record])
    with pytest.raises(EvalDatasetError):
        load_dataset(p)


def test_loader_reads_multiple_lines(tmp_path):
    p = _write(tmp_path, [_VALID, _VALID, _VALID])
    examples = load_dataset(p)
    assert len(examples) == 3
    assert all(isinstance(e, EvalExample) for e in examples)
