"""deploy/local-instance checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
Checks that observe a configuration choice return it as a note.
"""

import re

COLLECTION = "DocumentChunk"
MIN_SERVER_VERSION = "1.39.0"
DEFAULT_DATA_PATH = "/var/lib/weaviate"


def release_at_least(version: str | None, minimum: str) -> bool:
    """Accept stable ``X.Y.Z`` releases at or above ``minimum``."""
    parts = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version or "")
    return bool(parts) and tuple(map(int, parts.groups())) >= tuple(
        map(int, minimum.split("."))
    )


def container(snapshot: dict) -> dict:
    """Return the weaviate service container's recorded configuration."""
    assert snapshot["container"], (
        "a running Compose service named weaviate exists; found none"
    )
    return snapshot["container"]


def collection(snapshot: dict) -> dict:
    """Return the DocumentChunk class from the schema."""
    assert snapshot["collection"], (
        f"a {COLLECTION} collection exists; found {snapshot['collections']}"
    )
    return snapshot["collection"]


# --- Required ----------------------------------------------------------------


def weaviate_reachable(snapshot: dict) -> None:
    """/v1/meta answers HTTP 200 at WEAVIATE_HTTP_HOST and WEAVIATE_HTTP_PORT."""
    status = snapshot["meta"]["status"]
    assert status == 200, f"/v1/meta answers HTTP 200; got {status}"


def weaviate_ready(snapshot: dict) -> None:
    """/v1/.well-known/ready answers 2xx."""
    status = snapshot["ready_status"]
    assert 200 <= status < 300, f"/v1/.well-known/ready answers 2xx; got {status}"


def server_version(snapshot: dict) -> str:
    """The running backend reports Weaviate 1.39.0 or later."""
    # Reads the version the running server reports in /v1/meta.
    version = snapshot["meta"]["version"]
    assert release_at_least(version, MIN_SERVER_VERSION), (
        f"Weaviate is {MIN_SERVER_VERSION} or later; running {version}"
    )
    return f"version {version}"


def collection_vectorizer(snapshot: dict) -> str:
    """DocumentChunk configures a vectorizer module, as a named vector or at collection level."""
    # Weaviate 1.39 lists API-based vectorizers in /v1/meta by default, so the
    # collection definition, not the module list, records the agent's choice.
    config = collection(snapshot)
    named = {
        name: next(iter(vector.get("vectorizer") or {"none": None}))
        for name, vector in (config.get("vectorConfig") or {}).items()
    }
    legacy = config.get("vectorizer", "none")
    assert legacy != "none" or set(named.values()) - {"none"}, (
        f"{COLLECTION} configures a vectorizer module; named vectors: {named or 'none'}, "
        f"collection-level vectorizer: {legacy}"
    )
    return f"named vectors: {named or 'none'}; collection-level vectorizer: {legacy}"


# --- Preferred ---------------------------------------------------------------


def vectorizer_availability(snapshot: dict) -> str:
    """A probe object inserted into DocumentChunk gets a non-zero vector."""
    # The agent picks the model, so any non-zero dimension passes.
    # Preferred because a vectorizer needing an API key cannot run in the Trial.
    collection(snapshot)
    probe = snapshot["vector_probe"]
    assert probe["create_status"] < 300, (
        f"a probe object can be inserted; got {probe['create_status']}: {probe['create_body']}"
    )
    vectors = probe["vectors"]
    assert any(v["dimensions"] and v["nonzero"] for v in vectors.values()), (
        f"the probe object gets a non-zero vector; got {vectors or 'no vectors'}"
    )
    assert probe["delete_status"] < 300, "the probe object is removed"
    return f"vectors: {vectors}"


def named_vector(snapshot: dict) -> None:
    """DocumentChunk configures vectorization as a named vector, not the legacy
    collection-level vectorizer."""
    # Scores only the configuration shape; collection-vectorizer and
    # vectorizer-availability score the module and vector presence.
    config = collection(snapshot)
    legacy = config.get("vectorizer", "none")
    assert config.get("vectorConfig") and legacy == "none", (
        f"{COLLECTION} configures vectorization as a named vector; it uses the legacy "
        f"collection-level vectorizer ({legacy}) instead"
    )


def persistence_configured(snapshot: dict) -> str:
    """A volume or bind mount covers the weaviate container's PERSISTENCE_DATA_PATH."""
    config = container(snapshot)
    path = config["env"].get("PERSISTENCE_DATA_PATH", DEFAULT_DATA_PATH).rstrip("/")
    mounts = [
        m
        for m in config["mounts"]
        if path == m["Destination"].rstrip("/")
        or path.startswith(m["Destination"].rstrip("/") + "/")
    ]
    assert mounts, f"a mount covers the data path {path}; mounts: {config['mounts']}"
    return f"{path} on {mounts[0]['Type']} {mounts[0]['Name'] or mounts[0]['Source']}"


def auth_posture(snapshot: dict) -> str:
    """Records whether anonymous access is enabled and how many API keys are configured."""
    auth = snapshot["auth"]
    anonymous = (
        "refused"
        if auth["anonymous_status"] == 401
        else f"HTTP {auth['anonymous_status']}"
    )
    return f"anonymous /v1/schema: {anonymous}; API keys: {auth['api_key_count']}"


REQUIRED = [weaviate_reachable, weaviate_ready, server_version, collection_vectorizer]
PREFERRED = [
    vectorizer_availability,
    named_vector,
    persistence_configured,
    auth_posture,
]
