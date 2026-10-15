"""Capture the build/ecommerce-search Trial's live state for ``check.py``.

Weaviate is read over REST rather than the Python client so the snapshot does
not depend on the client version the agent installed. Vectors are reduced to
presence flags and named-vector names.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

COLLECTION = "Product"
WEAVIATE = f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"

INVALID = (0, -1, "abc", "1.5")
PAGINATION_QUERY = "useful equipment for home and travel"
# Label -> /search query parameters. check.py reads responses by label.
PROBES: dict[str, dict] = {
    "missing-query": {},
    **{f"invalid-page-{v}": {"query": "test", "page": v} for v in INVALID},
    **{f"invalid-page-size-{v}": {"query": "test", "page_size": v} for v in INVALID},
    "default-page": {"query": "travel equipment"},
    "exact-sku": {"query": "ZXQ-9917", "page": 1, "page_size": 5},
    "semantic": {"query": "soggy mountaineering trek", "page": 1, "page_size": 5},
    "pagination-reference": {"query": PAGINATION_QUERY, "page": 1, "page_size": 24},
    **{
        f"pagination-page-{n}": {"query": PAGINATION_QUERY, "page": n, "page_size": 5}
        for n in range(1, 6)
    },
    "pagination-page-1-repeat": {"query": PAGINATION_QUERY, "page": 1, "page_size": 5},
}


def get(url: str) -> tuple[int, object]:
    """GET a URL; return the status and JSON body (or raw text if not JSON)."""
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw.decode(errors="replace")


def objects(collection: str) -> list[dict]:
    """Return every object's properties and vector presence, paging by cursor."""
    result, after = [], None
    while True:
        params = {"class": collection, "limit": 100, "include": "vector"}
        if after:
            params["after"] = after
        _, body = get(f"{WEAVIATE}/v1/objects?{urllib.parse.urlencode(params)}")
        page = body.get("objects") or []
        for obj in page:
            vectors = obj.get("vectors") or {}
            result.append(
                {
                    "id": obj["id"],
                    "properties": obj.get("properties", {}),
                    "has_vector": bool(obj.get("vector")) or any(vectors.values()),
                    "vector_names": sorted(vectors),
                }
            )
        if len(page) < 100:
            return result
        after = page[-1]["id"]


def snapshot(app_url: str) -> dict:
    """Return Weaviate meta, schema, objects, /search probes, and submitted files."""
    _, meta = get(f"{WEAVIATE}/v1/meta")
    _, schema = get(f"{WEAVIATE}/v1/schema")
    probes = {}
    for label, params in PROBES.items():
        status, body = get(f"{app_url}/search?{urllib.parse.urlencode(params)}")
        probes[label] = {"params": params, "status": status, "body": body}
    files = {
        p.name: p.read_text(errors="replace")
        for p in sorted(Path("/app").glob("*"))
        if p.suffix in {".py", ".yaml", ".yml", ".txt", ".toml"} and p.is_file()
    }
    return {
        "weaviate_version": meta.get("version"),
        "schema": schema,
        "objects": {COLLECTION: objects(COLLECTION)},
        "probes": probes,
        "files": files,
        "fixture": json.loads(Path("/fixtures/products.json").read_text()),
    }
