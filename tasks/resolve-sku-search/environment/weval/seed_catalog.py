"""Seed the evaluator's Product catalog before agent execution.

``sku`` keeps Weaviate's default word tokenization, which splits ``ZXQ-9917``,
``9917-ZXQ``, and ``9917@ZXQ`` into the same tokens. Object UUIDs derive from the SKU so
``check.py`` can tell whether the agent preserved them.
"""

import json
import os
import time
import urllib.request
from pathlib import Path
from uuid import UUID, uuid5

COLLECTION = "Product"
NAMESPACE = UUID("6f1c1d0e-3b5a-4f7e-9a51-6c1f0e2d9b17")
BASE_URL = f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"
PRODUCTS = Path(__file__).with_name("products.json")


def request(path: str, payload: object | None = None) -> object:
    """GET (no payload) or POST JSON to Weaviate and return the decoded body."""
    req = urllib.request.Request(
        BASE_URL + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def seed() -> None:
    """Create Product and import the catalog in file order.

    Raises:
        RuntimeError: The import reports a failure or the count never reaches the catalog size.
    """
    products = json.loads(PRODUCTS.read_text())
    request("/v1/schema", {
        "class": COLLECTION,
        "vectorizer": "none",
        "properties": [
            {"name": "sku", "dataType": ["text"]},
            {"name": "name", "dataType": ["text"]},
            {"name": "description", "dataType": ["text"]},
            {"name": "category", "dataType": ["text"]},
            {"name": "price", "dataType": ["number"]},
        ],
    })
    batch = request("/v1/batch/objects", {"objects": [
        {"class": COLLECTION, "id": str(uuid5(NAMESPACE, p["sku"])), "properties": p}
        for p in products
    ]})
    if any(entry.get("result", {}).get("errors") for entry in batch):
        raise RuntimeError(f"catalog import failed: {batch}")

    query = {"query": "{ Aggregate { Product { meta { count } } } }"}
    for _ in range(30):
        if request("/v1/graphql", query)["data"]["Aggregate"][COLLECTION][0]["meta"]["count"] == len(products):
            return
        time.sleep(1)
    raise RuntimeError(f"Product did not reach {len(products)} objects")


if __name__ == "__main__":
    seed()
