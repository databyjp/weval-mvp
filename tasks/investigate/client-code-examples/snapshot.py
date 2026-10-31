"""Capture the investigate/client-code-examples Trial for ``check.py``.

The Task has no stack. The snapshot records the submitted ``findings.json``.
"""

import json
from pathlib import Path

FINDINGS = Path("/app/findings.json")


def findings() -> dict:
    """Return the submitted file's text and parsed value, or why it has neither."""
    if not FINDINGS.exists():
        return {"text": None, "parsed": None, "error": f"{FINDINGS} does not exist"}
    text = FINDINGS.read_text(errors="replace")
    try:
        return {"text": text, "parsed": json.loads(text), "error": None}
    except json.JSONDecodeError as error:
        return {"text": text, "parsed": None, "error": f"not JSON: {error}"}


def snapshot(app_url: str | None) -> dict:
    """Return the submitted findings. ``app_url`` is unused."""
    return {"findings": findings()}
