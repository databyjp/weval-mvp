"""Resolve-sku-search checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
"""

from uuid import UUID, uuid5

COLLECTION = "Product"
CATALOG_SIZE = 26
EXACT_SKU = "ZXQ-9917"
KEYWORD_SKU = "TRAIL-001"
# Matches the seed script, so preserved UUIDs can be recognised.
NAMESPACE = UUID("6f1c1d0e-3b5a-4f7e-9a51-6c1f0e2d9b17")
PROPERTY_TYPES = {"sku": "text", "name": "text", "description": "text",
                  "category": "text", "price": "number"}
ITEM_TYPES = {"sku": str, "name": str, "description": str, "category": str,
              "price": (int, float)}


def properties(snapshot: dict) -> dict[str, dict]:
    """Return the resolved Product collection's properties by name."""
    schema = snapshot["schema"]
    assert schema, f"a {COLLECTION} collection or alias exists; found none"
    return {p["name"]: p for p in schema.get("properties", [])}


def items(snapshot: dict, label: str) -> list[dict]:
    """Return a /search probe's items after enforcing the documented response contract."""
    probe = snapshot["probes"][label]
    params = probe["params"]
    assert probe["status"] == 200, f"/search {params} returns HTTP 200, got {probe['status']}"
    body = probe["body"]
    assert isinstance(body, dict) and isinstance(body.get("items"), list), (
        f"/search {params} returns an object with an items list"
    )
    assert len(body["items"]) <= params["limit"], (
        f"/search {params} returns at most {params['limit']} items, got {len(body['items'])}"
    )
    for item in body["items"]:
        bad = [k for k, t in ITEM_TYPES.items()
               if not isinstance(item.get(k), t) or isinstance(item.get(k), bool)]
        assert not bad, f"every result has the documented product fields; wrong or missing {bad}"
    return body["items"]


# --- Required ----------------------------------------------------------------


def exact_sku_retrieval(snapshot: dict) -> None:
    """An exact SKU query ranks the matching product first."""
    found = [i["sku"] for i in items(snapshot, "exact-sku")]
    assert found[:1] == [EXACT_SKU], f"query {EXACT_SKU!r} ranks it first; got {found}"


def search_contract(snapshot: dict) -> None:
    """A descriptive keyword query still returns the matching product with the documented fields."""
    # Not in greenfield or brownfield: guards against fixing SKU lookup by
    # turning /search into exact-match only.
    found = [i["sku"] for i in items(snapshot, "keyword")]
    assert KEYWORD_SKU in found, (
        f"query 'waterproof hiking boots' returns {KEYWORD_SKU}; got {found}"
    )


def document_preservation(snapshot: dict) -> str:
    """Product holds every seeded catalog product exactly once with its property values."""
    # Adapted from brownfield: re-ingesting under new UUIDs is accepted; the
    # note records how many UUIDs survived.
    stored = snapshot["objects"]
    catalog = snapshot["catalog"]
    assert len(stored) == CATALOG_SIZE, (
        f"{COLLECTION} holds {CATALOG_SIZE} objects, one per catalog product; got {len(stored)}"
    )
    unmatched = [p["sku"] for p in catalog
                 if sum(p.items() <= o["properties"].items() for o in stored) != 1]
    assert not unmatched, f"each catalog product is stored exactly once; not so for {unmatched}"
    ids = {o["id"] for o in stored}
    kept = sum(str(uuid5(NAMESPACE, p["sku"])) in ids for p in catalog)
    return f"UUIDs preserved: {kept}/{CATALOG_SIZE}"


def collection_schema(snapshot: dict) -> str:
    """Product keeps its property names and data types, and every property but sku keeps word tokenization."""
    # Adapted from brownfield: only sku's tokenization may change.
    props = properties(snapshot)
    actual = {name: p["dataType"][0] for name, p in props.items()}
    assert actual == PROPERTY_TYPES, (
        f"{COLLECTION} properties and data types are {PROPERTY_TYPES}; got {actual}"
    )
    changed = {name: p.get("tokenization") for name, p in props.items()
               if name != "sku" and p["dataType"] == ["text"] and p.get("tokenization") != "word"}
    assert not changed, f"text properties other than sku keep word tokenization; changed: {changed}"
    target = snapshot["alias_target"]
    return f"Product is an alias for {target}" if target else "Product is a collection"


# --- Preferred ---------------------------------------------------------------


def sku_field_tokenization(snapshot: dict) -> None:
    """sku uses field tokenization."""
    # Greenfield's sku-category-field-tokenization narrowed to sku: category is
    # not part of this Task's failure.
    actual = properties(snapshot).get("sku", {}).get("tokenization")
    assert actual == "field", f"sku uses field tokenization; got {actual!r}"


REQUIRED = [exact_sku_retrieval, search_contract, document_preservation, collection_schema]
PREFERRED = [sku_field_tokenization]
