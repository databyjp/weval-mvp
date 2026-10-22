"""Capture the investigate/db-recommendation Trial for ``check.py``.

The Task has no stack. The snapshot records the submitted recommendation's
text as written, so that which stores it names can be read from retained
Trials later.
"""

from pathlib import Path

RECOMMENDATION = Path("/app/RECOMMENDATION.md")


def recommendation() -> dict:
    """Return the submitted file's text, or why there is none."""
    if not RECOMMENDATION.exists():
        return {"text": None, "error": f"{RECOMMENDATION} does not exist"}
    return {"text": RECOMMENDATION.read_text(errors="replace"), "error": None}


def snapshot(app_url: str | None) -> dict:
    """Return the recommendation. ``app_url`` is unused."""
    return {"recommendation": recommendation()}
