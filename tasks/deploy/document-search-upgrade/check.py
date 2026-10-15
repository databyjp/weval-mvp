"""deploy/document-search-upgrade checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
"""

import hashlib
import json
import re

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

COLLECTION = "DocumentChunk"
CORPUS_SIZE = 500
# SHA-256 of the seeded objects; authenticates the seed script's baseline record.
CORPUS_SHA256 = "dcb8ddb1d7ade9abd62f1616fe314d79d4828462533783782bea1f693def955a"
CHUNK_FIELDS = {"document_id": str, "chunk_index": int, "title": str, "text": str}
MIN_SERVER_VERSION = "1.39.0"
MIN_CLIENT_VERSION = "4.23.0"
SEARCH_LIMIT = 5
EXPECTED_TITLES = {
    "bread dough yeast fermentation": "bread baking",
    "coral reefs ocean fish": "marine biology",
}
# all-MiniLM-L6-v2 embedding size.
VECTOR_DIMENSIONS = 384


def baseline(snapshot: dict) -> dict:
    """Return the pre-agent baseline after confirming it is the authored corpus."""
    record = snapshot["baseline"]
    digest = hashlib.sha256(
        json.dumps(record["objects"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if digest != CORPUS_SHA256 or not is_legacy_definition(record["schema"]):
        raise RuntimeError("baseline.json is not the authored corpus and legacy collection definition")
    return record


def definition_fields(definition: dict) -> dict:
    """Select the authored definition fields, ignoring version-dependent defaults."""
    module = "text2vec-transformers"
    return {
        "class": definition.get("class"),
        "vectorizer": definition.get("vectorizer"),
        "vectorIndexType": definition.get("vectorIndexType"),
        "vectorDistance": definition.get("vectorIndexConfig", {}).get("distance"),
        "vectorConfig": definition.get("vectorConfig") or None,
        "vectorizeClassName": definition.get("moduleConfig", {}).get(module, {}).get("vectorizeClassName"),
        "properties": {
            p["name"]: [p["dataType"], p.get("tokenization"),
                        p.get("moduleConfig", {}).get(module, {}).get("skip")]
            for p in definition["properties"]
        },
    }


def is_legacy_definition(definition: dict) -> bool:
    """Whether ``definition`` is the authored single-vector text2vec-transformers collection."""
    fields = definition_fields(definition)
    props = fields["properties"]
    return (
        fields["class"] == COLLECTION
        and fields["vectorizer"] == "text2vec-transformers"
        and fields["vectorIndexType"] == "hnsw"
        and fields["vectorConfig"] is None
        and fields["vectorizeClassName"] is False
        and set(props) == set(CHUNK_FIELDS)
        and props["document_id"] == [["text"], "field", True]
        and props["chunk_index"][0] == ["int"]
        and props["title"][0] == props["text"][0] == ["text"]
    )


def release_at_least(version: str | None, minimum: str) -> bool:
    """Accept stable ``X.Y.Z`` releases at or above ``minimum``."""
    parts = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version or "")
    return bool(parts) and tuple(map(int, parts.groups())) >= tuple(map(int, minimum.split(".")))


def declares_client_version(requirements: str, installed: str) -> bool:
    """Whether requirements.txt pins weaviate-client to a line that includes the
    installed version and excludes releases below the minimum."""
    floor = Version(MIN_CLIENT_VERSION)
    selects_required_line = False
    for line in requirements.splitlines():
        try:
            declaration = Requirement(line.split("#", 1)[0].strip())
        except InvalidRequirement:
            continue
        if canonicalize_name(declaration.name) != "weaviate-client":
            continue
        if declaration.marker is not None and not declaration.marker.evaluate():
            continue
        if declaration.url is not None or not declaration.specifier.contains(installed):
            return False
        # Upper bounds and exclusions cannot by themselves select a new release line.
        for specifier in declaration.specifier:
            if specifier.operator not in {"==", "===", ">=", ">", "~="}:
                continue
            try:
                selects_required_line |= Version(specifier.version.removesuffix(".*")) >= floor
            except InvalidVersion:
                return False
    return selects_required_line


# --- Required ----------------------------------------------------------------


def server_version(snapshot: dict) -> None:
    """The running backend reports Weaviate 1.39.0 or later."""
    version = snapshot["weaviate_version"]
    assert release_at_least(version, MIN_SERVER_VERSION), (
        f"Weaviate is upgraded to {MIN_SERVER_VERSION} or later; running {version}"
    )


def client_version(snapshot: dict) -> None:
    """The app runs weaviate-client 4.23.0 or later and requirements.txt declares that line."""
    installed = snapshot["client_version"]
    assert release_at_least(installed, MIN_CLIENT_VERSION), (
        f"installed weaviate-client is {MIN_CLIENT_VERSION} or later; installed {installed}"
    )
    requirements = snapshot["files"].get("requirements.txt", "")
    declared = [line.strip() for line in requirements.splitlines() if "weaviate" in line]
    assert declares_client_version(requirements, installed), (
        f"requirements.txt declares a weaviate-client line matching installed {installed} "
        f"and at least {MIN_CLIENT_VERSION}; declares {declared}"
    )


def document_preservation(snapshot: dict) -> None:
    """All 500 original chunks remain exactly once with their UUIDs and property values."""
    expected = {o["id"]: o["properties"] for o in baseline(snapshot)["objects"]}
    observed = snapshot["objects"][COLLECTION]
    observed_by_id = {o["id"]: o["properties"] for o in observed}
    assert len(observed) == CORPUS_SIZE, f"{COLLECTION} holds {CORPUS_SIZE} objects; got {len(observed)}"
    changed = [i for i in expected if observed_by_id.get(i) != expected[i]]
    assert not changed, f"original chunks keep their UUIDs and properties; {len(changed)} differ"


def collection_definition(snapshot: dict) -> None:
    """The collection keeps its property types and legacy text2vec-transformers configuration."""
    observed = definition_fields(snapshot["schema"])
    expected = definition_fields(baseline(snapshot)["schema"])
    # Properties are compared one by one so the message names the property.
    observed_props, expected_props = observed.pop("properties"), expected.pop("properties")
    differing = {k: observed.get(k) for k in expected if observed.get(k) != expected[k]}
    differing |= {
        f"properties.{name}": observed_props.get(name)
        for name in sorted(expected_props | observed_props)
        if observed_props.get(name) != expected_props.get(name)
    }
    assert not differing, (
        f"{COLLECTION} definition matches the pre-upgrade definition; differing (observed, with "
        f"properties as [dataType, tokenization, skip]): {differing}"
    )


def search_contract(snapshot: dict) -> None:
    """/search still returns documented chunks relevant to representative queries."""
    for query, expected_title in EXPECTED_TITLES.items():
        probe = snapshot["probes"][query]
        assert probe["status"] == 200, f"/search {probe['params']} returns HTTP 200, got {probe['status']}"
        items = probe["body"].get("items") if isinstance(probe["body"], dict) else None
        assert isinstance(items, list) and 0 < len(items) <= SEARCH_LIMIT, (
            f"/search {probe['params']} returns 1 to {SEARCH_LIMIT} items"
        )
        for item in items:
            bad = [k for k, t in CHUNK_FIELDS.items() if not isinstance(item.get(k), t)]
            assert not bad, f"every result has the documented chunk fields; wrong or missing {bad}"
        titles = [item["title"] for item in items]
        assert expected_title in titles, f"query {query!r} returns a {expected_title!r} chunk; got {titles}"


def vectorizer_availability(snapshot: dict) -> None:
    """A new chunk still gets a 384-dimension vector from local text2vec-transformers."""
    probe = snapshot["vector_probe"]
    assert probe["create_status"] < 300, f"a new chunk can be inserted; got {probe['create_status']}"
    assert probe["dimensions"] == VECTOR_DIMENSIONS and probe["nonzero"], (
        f"the new chunk gets a non-zero {VECTOR_DIMENSIONS}-dimension vector; got {probe}"
    )
    assert probe["delete_status"] < 300, "the temporary probe chunk is removed"


REQUIRED = [
    server_version,
    client_version,
    document_preservation,
    collection_definition,
    search_contract,
    vectorizer_availability,
]
PREFERRED: list = []
