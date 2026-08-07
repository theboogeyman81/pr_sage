from pathlib import Path

from app.llm.exceptions import PromptNotFoundError

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"


class PromptRegistry:
    def __init__(self, root: Path = _PROMPTS_ROOT) -> None:
        self._root = root

    def get(self, name: str, version: int) -> str:
        path = self._root / name / f"v{version}.md"
        if not path.exists():
            raise PromptNotFoundError(f"Prompt not found: {name}/v{version}")
        return path.read_text(encoding="utf-8")
