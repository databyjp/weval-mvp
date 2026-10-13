"""Migrate Product to field-tokenized SKUs behind a Product alias.

Tokenization cannot change on an existing property, so the Oracle copies every
object, with its UUID, into ProductV2, drops the original collection, and
points a Product alias at ProductV2. The app keeps querying "Product".
"""

import json
import os
import time
import urllib.parse
import urllib.request

BASE_URL = f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"
SOURCE, TARGET = "Product", "ProductV2"


def call(path: str, method: str = "GET", payload: object | None = None) -> object:
    req = urllib.request.Request(
        BASE_URL + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def objects(collection: str) -> list[dict]:
    result, after = [], None
    while True:
        params = {"class": collection, "limit": 100, **({"after": after} if after else {})}
        page = call(f"/v1/objects?{urllib.parse.urlencode(params)}")["objects"] or []
        result += page
        if len(page) < 100:
            return result
        after = page[-1]["id"]


source = call(f"/v1/schema/{SOURCE}")
properties = [
    {"name": p["name"], "dataType": p["dataType"],
     **({"tokenization": "field" if p["name"] == "sku" else p["tokenization"]}
        if "tokenization" in p else {})}
    for p in source["properties"]
]
call("/v1/schema", "POST", {"class": TARGET, "vectorizer": "none", "properties": properties})

catalog = objects(SOURCE)
call("/v1/batch/objects", "POST", {"objects": [
    {"class": TARGET, "id": o["id"], "properties": o["properties"]} for o in catalog
]})
for _ in range(30):
    if len(objects(TARGET)) == len(catalog):
        break
    time.sleep(1)
else:
    raise RuntimeError(f"{TARGET} did not reach {len(catalog)} objects")

call(f"/v1/schema/{SOURCE}", "DELETE")
call("/v1/aliases", "POST", {"alias": SOURCE, "class": TARGET})
