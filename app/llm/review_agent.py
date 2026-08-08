from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.analysis.finding import Finding
from app.llm.exceptions import ReviewError
from app.llm.gemini_client import GeminiClient
from app.llm.prompt_registry import PromptRegistry

_MAX_TOKENS = 4096


class Comment(BaseModel):
    path: str
    line: int
    body: str
    severity: Literal["error", "warning", "suggestion"]


def run_review(
    diff: str,
    context: str,
    findings: list[Finding],
    *,
    client: GeminiClient,
    registry: PromptRegistry,
    model: str,
    prompt_version: int = 1,
) -> list[Comment]:
    template = registry.get("review", prompt_version)

    findings_text = (
        "\n".join(f"{f.rule}: {f.message} ({f.path}:{f.line})" for f in findings)
        if findings
        else "None"
    )

    prompt_text = template.format(
        diff=diff,
        context=context,
        findings=findings_text,
    )

    messages = [{"role": "user", "parts": [{"text": prompt_text}]}]
    response = client.complete(messages, model=model, max_tokens=_MAX_TOKENS)

    try:
        raw = json.loads(response.content)
    except json.JSONDecodeError as exc:
        raise ReviewError(f"Model returned non-JSON: {exc}") from exc

    try:
        return [Comment.model_validate(item) for item in raw]
    except (ValidationError, TypeError) as exc:
        raise ReviewError(f"Comment validation failed: {exc}") from exc
