"""Capture the resolve/sku-search Trial's live, agent-fixed stack for ``check.py``.

The verifier keeps the agent's running stack (``WEVAL_KEEP_STACK=1``) because
its Weaviate volume holds the catalog under test. When ``Product`` is an alias,
the snapshot reads the collection it points to.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

COLLECTION = "Product"
WEAVIATE = f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"
# Label -> /search query parameters. check.py reads responses by label.
EXACT_SKUS = ("ZXQ-9917", "9917-ZXQ", "9917@ZXQ", "AQ1-9917", "ZXQ-4831",
              "zxq-9917", "ZXQ 9917", "9917 ZXQ")
PROBES = {
    **{f"exact-sku-{sku}": {"query": sku, "limit": 5} for sku in EXACT_SKUS},
    "keyword": {"query": "waterproof hiking boots", "limit": 5},
}


def request(url: str) -> tuple[int, object]:
    """GET a URL; return the status and JSON body (or raw text if not JSON).
    Connection failures and timeouts raise."""
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
    """Return every object's id and properties, paging by cursor."""
    result, after = [], None
    while True:
        params = {"class": collection, "limit": 100, **({"after": after} if after else {})}
        _, body = request(f"{WEAVIATE}/v1/objects?{urllib.parse.urlencode(params)}")
        page = body.get("objects") or []
        result += [{"id": o["id"], "properties": o.get("properties", {})} for o in page]
        if len(page) < 100:
            return result
        after = page[-1]["id"]


def snapshot(app_url: str) -> dict:
    """Return the resolved Product schema and objects, alias, /search probes, and catalog."""
    _, aliases = request(f"{WEAVIATE}/v1/aliases")
    alias = next((a for a in (aliases or {}).get("aliases") or [] if a["alias"] == COLLECTION), None)
    target = alias["class"] if alias else COLLECTION
    schema_status, schema = request(f"{WEAVIATE}/v1/schema/{target}")
    probes = {}
    for label, params in PROBES.items():
        status, body = request(f"{app_url}/search?{urllib.parse.urlencode(params)}")
        probes[label] = {"params": params, "status": status, "body": body}
    return {
        "alias_target": alias and target,
        "schema": schema if schema_status == 200 else None,
        "objects": objects(target),
        "probes": probes,
        "catalog": json.loads(Path("/opt/weval/products.json").read_text()),
    }
