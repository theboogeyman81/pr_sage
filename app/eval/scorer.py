from dataclasses import dataclass

from app.eval.schema import ExpectedFinding
from app.llm.review_agent import Comment


@dataclass
class CategoryResult:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float


def score(
    expected: list[ExpectedFinding],
    actual: list[Comment],
) -> dict[str, CategoryResult]:
    """
    Return per-category TP/FP/FN/precision/recall.

    Matching rule: a Comment matches an ExpectedFinding when
      comment.path == expected.path AND
      expected.line_range[0] <= comment.line <= expected.line_range[1].
    Each expected finding matches at most one comment (greedy, first match wins).
    FP = agent comments not matched to any expected finding; counted under "_unmatched".
    Results keyed by expected.category; "_unmatched" holds unmatched agent comments.
    """
    unmatched = list(actual)

    category_tp: dict[str, int] = {}
    category_fn: dict[str, int] = {}

    for exp in expected:
        cat = exp.category
        matched_idx = None
        for i, comment in enumerate(unmatched):
            if (comment.path == exp.path and
                    exp.line_range[0] <= comment.line <= exp.line_range[1]):
                matched_idx = i
                break

        if matched_idx is not None:
            category_tp[cat] = category_tp.get(cat, 0) + 1
            unmatched.pop(matched_idx)
        else:
            category_fn[cat] = category_fn.get(cat, 0) + 1

    results: dict[str, CategoryResult] = {}

    for cat in set(category_tp) | set(category_fn):
        tp = category_tp.get(cat, 0)
        fn = category_fn.get(cat, 0)
        precision = tp / tp if tp > 0 else 1.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        results[cat] = CategoryResult(tp=tp, fp=0, fn=fn,
                                      precision=precision, recall=recall)

    fp_count = len(unmatched)
    if fp_count > 0:
        results["_unmatched"] = CategoryResult(
            tp=0, fp=fp_count, fn=0, precision=0.0, recall=1.0
        )

    return results
