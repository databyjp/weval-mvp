"""Capture the investigate-defaults Trial's live state and submitted audit for ``check.py``.

There is no application. Every truth value is observed from the running
deployment at verification time, so an agent that changed the deployment is
scored against what it left. The default-vectorizer probe creates a scratch
collection with no vector configuration, records what Weaviate assigned, and
deletes it.
"""

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

WEAVIATE = f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"
AUDIT = Path("/app/audit.json")
PROBE_COLLECTION = "WevalDefaultVectorizerProbe"


def request(url: str, method: str = "GET", body: dict | None = None) -> tuple[int, object]:
    """Send a request; return the status and JSON body (or raw text if not JSON)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw.decode(errors="replace")


def container_env() -> dict[str, str] | None:
    """Return the Compose ``weaviate`` service container's environment, if running."""
    ids = subprocess.run(
        ["docker", "ps", "--quiet",
         "--filter", f"label=com.docker.compose.project={os.environ['COMPOSE_PROJECT_NAME']}",
         "--filter", "label=com.docker.compose.service=weaviate"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    if not ids:
        return None
    inspect = subprocess.run(["docker", "inspect", ids[0]],
                             capture_output=True, text=True, check=True)
    return dict(e.split("=", 1) for e in json.loads(inspect.stdout)[0]["Config"]["Env"])


def default_vectorizer_probe() -> dict:
    """Create a collection with no vector configuration, record its vectorizers, then drop it."""
    created, body = request(f"{WEAVIATE}/v1/schema", "POST", {
        "class": PROBE_COLLECTION,
        "properties": [{"name": "text", "dataType": ["text"]}],
    })
    deleted, _ = request(f"{WEAVIATE}/v1/schema/{PROBE_COLLECTION}", "DELETE")
    body = body if isinstance(body, dict) else {}
    return {
        "create_status": created,
        "vectorizer": body.get("vectorizer"),
        "named_vectors": {name: next(iter(v.get("vectorizer") or {"none": None}))
                          for name, v in (body.get("vectorConfig") or {}).items()},
        "delete_status": deleted,
    }


def audit() -> dict:
    """Return the submitted audit's raw text and parsed JSON, or why it could not be read."""
    if not AUDIT.is_file():
        return {"raw": None, "parsed": None, "error": f"{AUDIT} does not exist"}
    raw = AUDIT.read_text(errors="replace")
    try:
        return {"raw": raw, "parsed": json.loads(raw), "error": None}
    except json.JSONDecodeError as error:
        return {"raw": raw, "parsed": None, "error": f"{AUDIT} is not JSON: {error}"}


def snapshot(app_url: None) -> dict:
    """Return the live meta, auth posture, default-vectorizer probe, container env, and audit."""
    anonymous_status, _ = request(f"{WEAVIATE}/v1/schema")
    meta_status, meta = request(f"{WEAVIATE}/v1/meta")
    meta = meta if isinstance(meta, dict) else {}
    return {
        "meta": {"status": meta_status, "version": meta.get("version"),
                 "modules": sorted(meta.get("modules") or {})},
        "anonymous_status": anonymous_status,
        "default_vectorizer_probe": default_vectorizer_probe(),
        "container_env": container_env(),
        "audit": audit(),
    }
