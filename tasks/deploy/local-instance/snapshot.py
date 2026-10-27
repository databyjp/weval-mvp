"""Capture the deploy/local-instance Trial's live state for ``check.py``.

There is no application: the agent's running Weaviate is the artifact. The
snapshot reads the ``weaviate`` service container's configuration through the
Docker socket, the server and the ``DocumentChunk`` collection over REST, and
the vectors generated for one probe object, which it inserts and deletes.

When anonymous access is refused, REST reads use the first key in the
container's ``AUTHENTICATION_APIKEY_ALLOWED_KEYS``. Credential values are
redacted from the recorded container environment.
"""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request

WEAVIATE = (
    f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"
)
COLLECTION = "DocumentChunk"
VECTOR_PROBE_ID = "00000000-0000-4000-8000-00000000beef"
VECTOR_PROBE_TEXT = "This temporary chunk checks that Weaviate generates vectors."
SECRET_ENV = re.compile(r"(KEYS?|APIKEY|SECRET|TOKEN|PASSWORD)$")


def request(
    url: str, method: str = "GET", body: dict | None = None, key: str | None = None
) -> tuple[int, object]:
    """Send a request; return the status and JSON body (or raw text if not JSON).
    Connection failures and timeouts raise."""
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw.decode(errors="replace")


def weaviate_container() -> dict | None:
    """Return ``docker inspect`` for the Compose ``weaviate`` service, if running."""
    ids = subprocess.run(
        [
            "docker",
            "ps",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={os.environ['COMPOSE_PROJECT_NAME']}",
            "--filter",
            "label=com.docker.compose.service=weaviate",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    if not ids:
        return None
    inspect = subprocess.run(
        ["docker", "inspect", ids[0]], capture_output=True, text=True, check=True
    )
    return json.loads(inspect.stdout)[0]


def vector_probe(collection: dict, key: str | None) -> dict:
    """Insert one object with every text property set, summarise its vectors, then delete it."""
    text = {
        p["name"]: VECTOR_PROBE_TEXT
        for p in collection.get("properties", [])
        if p["dataType"] == ["text"]
    }
    url = f"{WEAVIATE}/v1/objects/{COLLECTION}/{VECTOR_PROBE_ID}"
    created, body = request(
        f"{WEAVIATE}/v1/objects",
        "POST",
        {"class": COLLECTION, "id": VECTOR_PROBE_ID, "properties": text},
        key,
    )
    _, fetched = request(f"{url}?include=vector", key=key)
    deleted, _ = request(url, "DELETE", key=key)
    fetched = fetched if isinstance(fetched, dict) else {}
    # A collection-level vector is reported under "default"; named vectors by name.
    vectors = fetched.get("vectors") or {}
    if fetched.get("vector"):
        vectors = {"default": fetched["vector"], **vectors}
    return {
        "create_status": created,
        "create_body": body if created >= 300 else None,
        "vectors": {
            name: {"dimensions": len(v), "nonzero": any(v)}
            for name, v in vectors.items()
        },
        "delete_status": deleted,
    }


def snapshot(app_url: None) -> dict:
    """Return the container config, auth posture, meta, readiness, collection, and vector probe."""
    container = weaviate_container()
    env = dict(
        e.split("=", 1) for e in (container or {}).get("Config", {}).get("Env", [])
    )

    anonymous_status, _ = request(f"{WEAVIATE}/v1/schema")
    keys = [
        k for k in env.get("AUTHENTICATION_APIKEY_ALLOWED_KEYS", "").split(",") if k
    ]
    key = keys[0] if anonymous_status == 401 and keys else None

    meta_status, meta = request(f"{WEAVIATE}/v1/meta", key=key)
    ready_status, _ = request(f"{WEAVIATE}/v1/.well-known/ready")
    _, schema = request(f"{WEAVIATE}/v1/schema", key=key)
    classes = (
        {c["class"]: c for c in schema.get("classes") or []}
        if isinstance(schema, dict)
        else {}
    )
    collection = classes.get(COLLECTION)

    return {
        "container": container
        and {
            "image": container["Config"]["Image"],
            "env": {
                k: "<redacted>" if SECRET_ENV.search(k) else v
                for k, v in sorted(env.items())
            },
            "mounts": [
                {k: m.get(k) for k in ("Type", "Name", "Source", "Destination")}
                for m in container.get("Mounts", [])
            ],
        },
        "auth": {
            "anonymous_status": anonymous_status,
            "api_key_count": len(keys),
            "used_api_key": key is not None,
        },
        "meta": {
            "status": meta_status,
            "version": meta.get("version") if isinstance(meta, dict) else None,
        },
        "ready_status": ready_status,
        "collections": sorted(classes),
        "collection": collection,
        "vector_probe": collection and vector_probe(collection, key),
    }
