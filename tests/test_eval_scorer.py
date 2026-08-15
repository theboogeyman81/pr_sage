from app.eval.schema import ExpectedFinding
from app.eval.scorer import score
from app.llm.review_agent import Comment


def _exp(path="app/foo.py", line_range=(1, 5), category="bare-except"):
    return ExpectedFinding(path=path, line_range=line_range, category=category)


def _comment(path="app/foo.py", line=3, severity="error"):
    return Comment(path=path, line=line, body="issue", severity=severity)


def test_perfect_match():
    result = score([_exp()], [_comment(line=3)])
    assert "bare-except" in result
    r = result["bare-except"]
    assert r.tp == 1 and r.fn == 0
    assert r.recall == 1.0
    assert "_unmatched" not in result


def test_missed_finding():
    result = score([_exp()], [])
    r = result["bare-except"]
    assert r.tp == 0 and r.fn == 1
    assert r.recall == 0.0


def test_unmatched_comment_goes_to_fp():
    result = score([], [_comment()])
    assert "_unmatched" in result
    assert result["_unmatched"].fp == 1
    assert result["_unmatched"].precision == 0.0


def test_comment_outside_line_range_is_unmatched():
    result = score([_exp(line_range=(1, 5))], [_comment(line=10)])
    assert result["bare-except"].tp == 0
    assert result["bare-except"].fn == 1
    assert result["_unmatched"].fp == 1


def test_different_path_does_not_match():
    result = score([_exp(path="app/foo.py")], [_comment(path="app/bar.py", line=3)])
    assert result["bare-except"].fn == 1
    assert result["_unmatched"].fp == 1


def test_two_expected_same_category_both_matched():
    exps = [_exp(line_range=(1, 5)), _exp(line_range=(10, 15))]
    comments = [_comment(line=3), _comment(line=12)]
    result = score(exps, comments)
    assert result["bare-except"].tp == 2
    assert result["bare-except"].fn == 0
    assert "_unmatched" not in result


def test_greedy_first_match_wins():
    # Two comments could match the same expected finding; only one should be consumed
    exps = [_exp(line_range=(1, 10))]
    comments = [_comment(line=3), _comment(line=7)]
    result = score(exps, comments)
    assert result["bare-except"].tp == 1
    # second comment is unmatched FP
    assert result["_unmatched"].fp == 1


def test_multiple_categories():
    exps = [
        _exp(category="bare-except", line_range=(1, 5)),
        _exp(category="missing-docstring", line_range=(10, 15)),
    ]
    comments = [_comment(line=3)]  # matches bare-except only
    result = score(exps, comments)
    assert result["bare-except"].tp == 1
    assert result["missing-docstring"].fn == 1
    assert "_unmatched" not in result


def test_empty_inputs():
    result = score([], [])
    assert result == {}
