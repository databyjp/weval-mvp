"""resolve/sku-search checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
"""

COLLECTION = "Product"
CATALOG_SIZE = 31
# ZXQ-9917 is the reported SKU. The others share its segments: 9917-ZXQ and
# 9917@ZXQ tokenize identically under word tokenization, and AQ1-9917 and
# ZXQ-4831 share one token. zxq-9917 differs only in case, so lowercase
# tokenization ties it with ZXQ-9917; ZXQ 9917 and 9917 ZXQ differ only in
# word order, so whitespace tokenization ties them. Only field tokenization
# separates every pair.
EXACT_SKUS = (
    "ZXQ-9917",
    "9917-ZXQ",
    "9917@ZXQ",
    "AQ1-9917",
    "ZXQ-4831",
    "zxq-9917",
    "ZXQ 9917",
    "9917 ZXQ",
)
KEYWORD_SKU = "TRAIL-001"
PROPERTY_TYPES = {
    "sku": "text",
    "name": "text",
    "description": "text",
    "category": "text",
    "price": "number",
}
ITEM_TYPES = {
    "sku": str,
    "name": str,
    "description": str,
    "category": str,
    "price": (int, float),
}


def properties(snapshot: dict) -> dict[str, dict]:
    """Return the resolved Product collection's properties by name."""
    schema = snapshot["schema"]
    assert schema, f"a {COLLECTION} collection or alias exists; found none"
    return {p["name"]: p for p in schema.get("properties", [])}


def items(snapshot: dict, label: str) -> list[dict]:
    """Return a /search probe's items after enforcing the documented response contract."""
    probe = snapshot["probes"][label]
    params = probe["params"]
    assert probe["status"] == 200, (
        f"/search {params} returns HTTP 200, got {probe['status']}"
    )
    body = probe["body"]
    assert isinstance(body, dict) and isinstance(body.get("items"), list), (
        f"/search {params} returns an object with an items list"
    )
    assert len(body["items"]) <= params["limit"], (
        f"/search {params} returns at most {params['limit']} items, got {len(body['items'])}"
    )
    for item in body["items"]:
        bad = [
            k
            for k, t in ITEM_TYPES.items()
            if not isinstance(item.get(k), t) or isinstance(item.get(k), bool)
        ]
        assert not bad, (
            f"every result has the documented product fields; wrong or missing {bad}"
        )
    return body["items"]


# --- Required ----------------------------------------------------------------


def exact_sku_retrieval(snapshot: dict) -> None:
    """An exact SKU query ranks the matching product first, for each SKU sharing segments with ZXQ-9917."""
    # Probes every colliding SKU, not ZXQ-9917 alone. A workaround that hoisted
    # word-tokenized filter matches ahead of BM25 results ranked ZXQ-9917 first
    # only because of seed order
    # (20261013-214112-resolve-sku-search-pi-glm-5.3-flash, Trial HrrRY7G).
    misranked = {}
    for sku in EXACT_SKUS:
        found = [i["sku"] for i in items(snapshot, f"exact-sku-{sku}")]
        if found[:1] != [sku]:
            misranked[sku] = found
    assert not misranked, f"each SKU query ranks that SKU first; got {misranked}"


def search_contract(snapshot: dict) -> None:
    """A descriptive keyword query still returns the matching product with the documented fields."""
    # Rejects fixing SKU lookup by turning /search into exact-match only.
    found = [i["sku"] for i in items(snapshot, "keyword")]
    assert KEYWORD_SKU in found, (
        f"query 'waterproof hiking boots' returns {KEYWORD_SKU}; got {found}"
    )


def document_preservation(snapshot: dict) -> None:
    """Product holds every seeded catalog product exactly once with its property values."""
    # Matches objects by property values, not UUID, so re-ingesting under new
    # UUIDs passes.
    stored = snapshot["objects"]
    catalog = snapshot["catalog"]
    assert len(stored) == CATALOG_SIZE, (
        f"{COLLECTION} holds {CATALOG_SIZE} objects, one per catalog product; got {len(stored)}"
    )
    unmatched = [
        p["sku"]
        for p in catalog
        if sum(p.items() <= o["properties"].items() for o in stored) != 1
    ]
    assert not unmatched, (
        f"each catalog product is stored exactly once; not so for {unmatched}"
    )


def collection_definition(snapshot: dict) -> str:
    """Product keeps its property names and data types."""
    actual = {name: p["dataType"][0] for name, p in properties(snapshot).items()}
    assert actual == PROPERTY_TYPES, (
        f"{COLLECTION} properties and data types are {PROPERTY_TYPES}; got {actual}"
    )
    target = snapshot["alias_target"]
    return f"Product is an alias for {target}" if target else "Product is a collection"


def sku_field_tokenization(snapshot: dict) -> None:
    """sku uses field tokenization."""
    # Required, so a fix that only reorders results in the app fails the Trial.
    # category is not checked: it is not part of this Task's fault.
    actual = properties(snapshot).get("sku", {}).get("tokenization")
    assert actual == "field", f"sku uses field tokenization; got {actual!r}"


# --- Preferred ---------------------------------------------------------------


def other_properties_word_tokenization(snapshot: dict) -> None:
    """Every seeded text property but sku keeps word tokenization."""
    # The fault is confined to sku. Preferred because neither the prompt nor
    # the workspace says to leave the other properties alone. A property whose
    # data type changed is collection-definition's failure, not this check's.
    props = properties(snapshot)
    changed = {
        name: props.get(name, {}).get("tokenization")
        for name, data_type in PROPERTY_TYPES.items()
        if name != "sku"
        and data_type == "text"
        and props.get(name, {}).get("tokenization") != "word"
    }
    assert not changed, (
        f"text properties other than sku keep word tokenization; changed: {changed}"
    )


REQUIRED = [
    exact_sku_retrieval,
    search_contract,
    document_preservation,
    collection_definition,
    sku_field_tokenization,
]
PREFERRED = [other_properties_word_tokenization]
