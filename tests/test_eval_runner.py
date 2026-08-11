import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.eval._cost import _CostAccumulator
from app.eval.runner import _check_threshold, run_eval
from app.eval.scorer import CategoryResult
from app.llm.cost_table import estimate_cost
from app.llm.exceptions import ReviewError
from app.llm.gemini_client import GeminiResponse
from app.llm.review_agent import Comment

_MODEL = "gemini-2.0-flash"

_EXAMPLE_LINE = json.dumps({
    "diff": "diff --git a/app/foo.py b/app/foo.py\n+x=1\n",
    "context": "x=1",
    "expected_findings": [{"path": "app/foo.py", "line_range": [1, 2], "category": "bare-except"}],
    "notes": "",
})

_COMMENT = Comment(path="app/foo.py", line=1, body="bare except", severity="error")
_RESULT = {"bare-except": CategoryResult(tp=1, fp=0, fn=0, precision=1.0, recall=1.0)}


def _make_dataset(tmp_path: Path) -> Path:
    p = tmp_path / "data.jsonl"
    p.write_text(_EXAMPLE_LINE, encoding="utf-8")
    return p


def test_run_eval_writes_report_file(tmp_path):
    dataset = _make_dataset(tmp_path)
    out_dir = tmp_path / "reports"
    with (
        patch("app.eval.runner.GeminiClient"),
        patch("app.eval.runner.run_review", return_value=[_COMMENT]),
        patch("app.eval.runner.score", return_value=_RESULT),
    ):
        report_path = run_eval(dataset, model=_MODEL, prompt_version=2, output_dir=out_dir)
    assert report_path.exists()
    assert report_path.suffix == ".json"


def test_report_has_required_keys(tmp_path):
    dataset = _make_dataset(tmp_path)
    out_dir = tmp_path / "reports"
    with (
        patch("app.eval.runner.GeminiClient"),
        patch("app.eval.runner.run_review", return_value=[_COMMENT]),
        patch("app.eval.runner.score", return_value=_RESULT),
    ):
        report_path = run_eval(dataset, model=_MODEL, prompt_version=2, output_dir=out_dir)
    report = json.loads(report_path.read_text())
    for key in ("timestamp", "model", "prompt_version", "dataset",
                "total_examples", "skipped_examples", "total_cost_usd",
                "by_category", "overall"):
        assert key in report, f"missing key: {key}"
    assert report["total_examples"] == 1
    assert report["model"] == _MODEL


def test_skipped_examples_counted(tmp_path):
    dataset = _make_dataset(tmp_path)
    out_dir = tmp_path / "reports"
    with (
        patch("app.eval.runner.GeminiClient"),
        patch("app.eval.runner.run_review", side_effect=ReviewError("bad json")),
        patch("app.eval.runner.score", return_value=_RESULT),
    ):
        report_path = run_eval(dataset, model=_MODEL, prompt_version=2, output_dir=out_dir)
    report = json.loads(report_path.read_text())
    assert report["skipped_examples"] == 1
    assert report["total_examples"] == 1


def test_check_threshold_passes_when_precision_above():
    report = {"overall": {"precision": 0.8, "recall": 0.7}}
    assert _check_threshold(report, 0.5) is True


def test_check_threshold_fails_when_precision_below():
    report = {"overall": {"precision": 0.3, "recall": 0.7}}
    assert _check_threshold(report, 0.5) is False


def test_cost_accumulator_sums_tokens():
    inner = MagicMock()
    inner.complete.side_effect = [
        GeminiResponse(content="a", input_tokens=10, output_tokens=5),
        GeminiResponse(content="b", input_tokens=20, output_tokens=10),
    ]
    acc = _CostAccumulator(inner)
    acc.complete([], model=_MODEL, max_tokens=100)
    acc.complete([], model=_MODEL, max_tokens=100)
    expected = estimate_cost(_MODEL, 30, 15)
    assert acc.total_cost_usd(_MODEL) == pytest.approx(expected)
