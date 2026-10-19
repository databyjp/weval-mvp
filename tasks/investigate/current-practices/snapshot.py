"""Capture the investigate/current-practices Trial for ``check.py``.

The Task has no stack. The snapshot records the submitted ``findings.json`` and
the latest releases at verify time, because later criteria compare answers
with releases that change after the Trial.
"""

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

FINDINGS = Path("/app/findings.json")
SERVER_RELEASES = "https://api.github.com/repos/weaviate/weaviate/releases?per_page=100"
CLIENT_RELEASES = "https://pypi.org/pypi/weaviate-client/json"


def request(url: str) -> tuple[int | None, object]:
    """GET a URL; return the status and JSON body (or raw text if not JSON).
    A connection failure or timeout returns ``(None, <error text>)`` rather
    than raising, so one unreachable host cannot cost the whole snapshot."""
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    except OSError as error:
        return None, str(error)
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw.decode(errors="replace")


def findings() -> dict:
    """Return the submitted file's text and parsed value, or why it has neither."""
    if not FINDINGS.exists():
        return {"text": None, "parsed": None, "error": f"{FINDINGS} does not exist"}
    text = FINDINGS.read_text(errors="replace")
    try:
        return {"text": text, "parsed": json.loads(text), "error": None}
    except json.JSONDecodeError as error:
        return {"text": text, "parsed": None, "error": f"not JSON: {error}"}


def latest_server_release() -> dict:
    """Return the highest stable ``X.Y.Z`` release among GitHub's 100 most recent,
    or the failed response."""
    # Highest version, not GitHub's "latest" flag: patch releases of older
    # minor lines are published after newer minors.
    status, body = request(SERVER_RELEASES)
    if status != 200 or not isinstance(body, list):
        return {"version": None, "status": status, "error": str(body)[:500]}
    versions = [
        tuple(map(int, match.groups()))
        for release in body
        if not release["draft"] and not release["prerelease"]
        and (match := re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", release["tag_name"]))
    ]
    return {"version": ".".join(map(str, max(versions))) if versions else None,
            "status": status, "error": None}


def latest_client_release() -> dict:
    """Return PyPI's current weaviate-client version, or the failed response."""
    status, body = request(CLIENT_RELEASES)
    if status != 200 or not isinstance(body, dict):
        return {"version": None, "status": status, "error": str(body)[:500]}
    return {"version": body["info"]["version"], "status": status, "error": None}


def snapshot(app_url: str | None) -> dict:
    """Return the findings and the latest releases. ``app_url`` is unused."""
    return {
        "findings": findings(),
        "latest_releases": {
            "weaviate": latest_server_release(),
            "weaviate-client": latest_client_release(),
        },
    }
