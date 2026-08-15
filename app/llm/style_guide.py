from pathlib import Path

import yaml

_DEFAULT_PATH = Path(__file__).parent.parent.parent / "style_guide.yaml"


class StyleGuideError(Exception):
    """Raised when style_guide.yaml is missing, malformed, or has invalid schema."""


def load_style_guide(path: Path = _DEFAULT_PATH) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StyleGuideError(f"Style guide not found: {path}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise StyleGuideError(f"Invalid YAML in style guide: {exc}") from exc

    if not isinstance(data, dict) or "rules" not in data:
        raise StyleGuideError("style_guide.yaml must have a top-level 'rules' key")

    rules = data["rules"]
    if not isinstance(rules, list) or not rules:
        raise StyleGuideError("'rules' must be a non-empty list")

    return "\n".join(f"- {r['name']}: {r['description']}" for r in rules)
