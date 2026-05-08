"""Prompt template loader for Growth OS agents.

Reads .md prompt files from the prompts/ directory and renders them
with Jinja2-style variable substitution.
"""

from __future__ import annotations

import os
from pathlib import Path


class PromptLoader:
    """Load and render prompt templates from disk."""

    def __init__(self, prompts_dir: str | None = None) -> None:
        self._dir = Path(
            prompts_dir
            or os.getenv("PROMPTS_DIR")
            or Path(__file__).resolve().parent.parent.parent.parent / "prompts"
        )

    def load(self, name: str, **variables: str) -> str:
        """Load prompt file `name.md`, substitute {{ var }} placeholders."""
        path = self._dir / f"{name}.md"
        text = path.read_text(encoding="utf-8")
        for key, value in variables.items():
            text = text.replace(f"{{{{ {key} }}}}", str(value))
        return text
