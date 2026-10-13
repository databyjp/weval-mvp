"""Write the Oracle's audit of the running deployment from live REST observations."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

WEAVIATE = f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"
VECTORIZER_PREFIXES = ("text2vec-", "multi2vec-", "text2multivec-", "multi2multivec-",
                       "img2vec-", "ref2vec-")


def call(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{WEAVIATE}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        return error.code, {}


anonymous_status, _ = call("/v1/schema")
_, meta = call("/v1/meta")

# Observe the default directly: what does a collection get when nothing is configured?
_, probe = call("/v1/schema", "POST", {"class": "OracleDefaultProbe",
                                       "properties": [{"name": "text", "dataType": ["text"]}]})
call("/v1/schema/OracleDefaultProbe", "DELETE")
default = probe.get("vectorizer")

Path("/app/audit.json").write_text(json.dumps({
    "server_version": meta["version"],
    "vectorizer_modules": sorted(m for m in meta["modules"] if m.startswith(VECTORIZER_PREFIXES)),
    "default_vectorizer": None if default in (None, "none") else default,
    "anonymous_access": anonymous_status == 200,
}, indent=2) + "\n")
