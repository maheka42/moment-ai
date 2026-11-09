"""Workflow prompt orchestration for corporate and student modes."""
from ..prompts import build_prompt


def build_workflow_prompt(mode: str, source_text: str) -> str:
    if not source_text.strip():
        raise ValueError("Source material cannot be empty.")
    return build_prompt(mode, source_text.strip())
