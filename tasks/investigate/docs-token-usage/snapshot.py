"""Capture the investigate/docs-token-usage Trial for ``check.py``.

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
SERVER_RELEASES_FEED = "https://github.com/weaviate/weaviate/releases.atom"
STABLE_TAG = r"v?(\d+)\.(\d+)\.(\d+)"
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
    or among the releases feed's 10 most recent when the API refuses, or the
    failed response. ``source`` names the URL the version came from."""
    # Highest version, not GitHub's "latest" flag: patch releases of older
    # minor lines are published after newer minors.
    status, body = request(SERVER_RELEASES)
    if status == 200 and isinstance(body, list):
        tags = [r["tag_name"] for r in body if not r["draft"] and not r["prerelease"]]
        return {
            "version": highest_stable(tags),
            "source": SERVER_RELEASES,
            "status": status,
            "error": None,
        }
    # The API's unauthenticated limit is per IP, and Trials share Modal's
    # egress IPs with agents that query the same API; the feed is not
    # counted against it. The feed omits drafts, and STABLE_TAG excludes
    # prerelease tags such as v1.40.0-rc.2.
    feed_status, feed = request(SERVER_RELEASES_FEED)
    if feed_status == 200 and isinstance(feed, str):
        tags = re.findall(r'/releases/tag/([^"]+)"', feed)
        return {
            "version": highest_stable(tags),
            "source": SERVER_RELEASES_FEED,
            "status": feed_status,
            "error": None,
        }
    return {
        "version": None,
        "source": None,
        "status": status,
        "error": f"API: {str(body)[:500]}; feed: {str(feed)[:500]}",
    }


def highest_stable(tags: list[str]) -> str | None:
    """Return the highest ``X.Y.Z`` among ``tags``, without a ``v`` prefix."""
    versions = [
        tuple(map(int, m.groups()))
        for tag in tags
        if (m := re.fullmatch(STABLE_TAG, tag))
    ]
    return ".".join(map(str, max(versions))) if versions else None


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
