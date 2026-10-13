"""Capture the brownfield Trial's live, agent-upgraded stack for ``check.py``.

The verifier keeps the agent's running stack (``WEVAL_KEEP_STACK=1`` in
``task.toml``) because its Weaviate volume holds the data under test.
``/logs/verifier/baseline.json`` is the pre-agent corpus and schema written by
the environment's seed script. The vector probe briefly inserts one object and
deletes it again.
"""

import importlib.metadata
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

COLLECTION = "DocumentChunk"
WEAVIATE = f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"
SEARCH_QUERIES = ("bread dough yeast fermentation", "coral reefs ocean fish")
VECTOR_PROBE_ID = "00000000-0000-4000-8000-00000000beef"
VECTOR_PROBE = {
    "document_id": "VERIFY-ONLY",
    "chunk_index": 0,
    "title": "temporary search check",
    "text": "This temporary chunk checks local transformer inference.",
}


def request(url: str, method: str = "GET", payload: object = None) -> tuple[int, object]:
    """Send a request; return the status and JSON body (or raw text if not JSON)."""
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    try:
        return status, json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return status, raw.decode(errors="replace")


def objects() -> list[dict]:
    """Return every object's id, properties, and vector presence, paging by cursor."""
    result, after = [], None
    while True:
        params = {"class": COLLECTION, "limit": 100, "include": "vector"}
        if after:
            params["after"] = after
        _, body = request(f"{WEAVIATE}/v1/objects?{urllib.parse.urlencode(params)}")
        page = body.get("objects") or []
        result += [
            {
                "id": o["id"],
                "properties": o.get("properties", {}),
                "has_vector": bool(o.get("vector")) or any((o.get("vectors") or {}).values()),
            }
            for o in page
        ]
        if len(page) < 100:
            return result
        after = page[-1]["id"]


def vector_probe() -> dict:
    """Insert one object, summarise the vector Weaviate generated, then delete it."""
    created, body = request(
        f"{WEAVIATE}/v1/objects",
        "POST",
        {"class": COLLECTION, "id": VECTOR_PROBE_ID, "properties": VECTOR_PROBE},
    )
    _, fetched = request(f"{WEAVIATE}/v1/objects/{COLLECTION}/{VECTOR_PROBE_ID}?include=vector")
    deleted, _ = request(f"{WEAVIATE}/v1/objects/{COLLECTION}/{VECTOR_PROBE_ID}", "DELETE")
    vector = fetched.get("vector") if isinstance(fetched, dict) else None
    numeric = isinstance(vector, list) and all(
        isinstance(v, (int, float)) and math.isfinite(v) for v in vector
    )
    return {
        "create_status": created,
        "create_body": body if created >= 300 else None,
        "dimensions": len(vector) if isinstance(vector, list) else None,
        "finite_numbers": numeric,
        "nonzero": numeric and any(v != 0 for v in vector),
        "delete_status": deleted,
    }


def snapshot(app_url: str) -> dict:
    """Return versions, schema, objects, baseline, /search probes, and a vector probe."""
    _, meta = request(f"{WEAVIATE}/v1/meta")
    _, schema = request(f"{WEAVIATE}/v1/schema/{COLLECTION}")
    probes = {}
    for query in SEARCH_QUERIES:
        params = {"query": query, "limit": 5}
        status, body = request(f"{app_url}/search?{urllib.parse.urlencode(params)}")
        probes[query] = {"params": params, "status": status, "body": body}
    try:
        client_version = importlib.metadata.version("weaviate-client")
    except importlib.metadata.PackageNotFoundError:
        client_version = None
    return {
        "weaviate_version": meta.get("version"),
        "client_version": client_version,
        "schema": schema,
        "objects": {COLLECTION: objects()},
        "probes": probes,
        "vector_probe": vector_probe(),
        "files": {
            p.name: p.read_text(errors="replace")
            for p in sorted(Path("/app").glob("*"))
            if p.suffix in {".py", ".yaml", ".yml", ".txt", ".toml"} and p.is_file()
        },
        "baseline": json.loads(Path("/logs/verifier/baseline.json").read_text()),
    }
