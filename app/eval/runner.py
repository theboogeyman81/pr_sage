import argparse
import json
import structlog
from datetime import datetime, timezone
from pathlib import Path

from app.eval._cost import _CostAccumulator
from app.eval.schema import load_dataset
from app.eval.scorer import score
from app.llm.exceptions import ReviewError
from app.llm.gemini_client import GeminiClient
from app.llm.prompt_registry import PromptRegistry
from app.llm.review_agent import run_review

logger = structlog.get_logger()


def run_eval(
    dataset_path: Path,
    *,
    model: str,
    prompt_version: int,
    output_dir: Path,
) -> Path:
    examples = load_dataset(dataset_path)
    registry = PromptRegistry()
    accumulator = _CostAccumulator(GeminiClient())

    accumulated: dict[str, dict[str, int]] = {}
    skipped = 0

    for ex in examples:
        try:
            comments = run_review(
                ex.diff, ex.context, [],
                client=accumulator, registry=registry,
                model=model, prompt_version=prompt_version,
            )
        except ReviewError as exc:
            logger.warning("eval_skip", reason=str(exc))
            skipped += 1
            continue

        results = score(ex.expected_findings, comments)
        for category, r in results.items():
            acc = accumulated.setdefault(category, {"tp": 0, "fp": 0, "fn": 0})
            acc["tp"] += r.tp
            acc["fp"] += r.fp
            acc["fn"] += r.fn

    by_category = {}
    total_tp = total_fp = total_fn = 0
    for category, counts in accumulated.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        by_category[category] = {"tp": tp, "fp": fp, "fn": fn,
                                  "precision": precision, "recall": recall}
        total_tp += tp
        total_fp += fp
        total_fn += fn

    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    overall_recall    = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0

    model_slug = model.replace("/", "-")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"{ts}_{model_slug}.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_version": prompt_version,
        "dataset": str(dataset_path),
        "total_examples": len(examples),
        "skipped_examples": skipped,
        "total_cost_usd": accumulator.total_cost_usd(model),
        "by_category": by_category,
        "overall": {"precision": overall_precision, "recall": overall_recall},
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("eval_complete", report=str(report_path),
                total=len(examples), skipped=skipped)
    return report_path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run eval against labeled dataset")
    parser.add_argument("--dataset", default="eval_data/seed.jsonl")
    parser.add_argument("--model", default="gemini-2.0-flash")
    parser.add_argument("--prompt-version", type=int, default=2)
    parser.add_argument("--output-dir", default="eval_reports")
    args = parser.parse_args()
    path = run_eval(
        Path(args.dataset),
        model=args.model,
        prompt_version=args.prompt_version,
        output_dir=Path(args.output_dir),
    )
    print(f"Report written to: {path}")


if __name__ == "__main__":
    _main()
