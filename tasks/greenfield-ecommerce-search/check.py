"""Greenfield ecommerce search checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
"""

COLLECTION = "Product"
DEFAULT_PAGE_SIZE = 5
EXACT_SKU = "ZXQ-9917"
SEMANTIC_SKU = "TRAIL-001"
PAGINATION_PAGES = 5
PAGINATION_REFERENCE_SIZE = 24
PROPERTY_TYPES = {"sku": "text", "name": "text", "description": "text",
                  "category": "text", "price": "number"}
ITEM_TYPES = {"sku": str, "name": str, "description": str, "category": str,
              "price": (int, float)}
# Modules covered by the Oracle and calibration; others are not scored as passing.
LOCAL_VECTORIZERS = {"text2vec-ollama", "text2vec-transformers"}


def collection(snapshot: dict) -> dict:
    """Return the Product class from the schema."""
    classes = {c["class"]: c for c in snapshot["schema"].get("classes") or []}
    assert COLLECTION in classes, f"a {COLLECTION} collection exists; found {sorted(classes)}"
    return classes[COLLECTION]


def properties(snapshot: dict) -> dict[str, dict]:
    return {p["name"]: p for p in collection(snapshot).get("properties", [])}


def items(snapshot: dict, label: str) -> list[dict]:
    """Return a /search probe's items after enforcing the documented response contract."""
    probe = snapshot["probes"][label]
    params = probe["params"]
    page, page_size = params.get("page", 1), params.get("page_size", DEFAULT_PAGE_SIZE)
    assert probe["status"] == 200, f"/search {params} returns HTTP 200, got {probe['status']}"
    body = probe["body"]
    assert isinstance(body, dict) and isinstance(body.get("items"), list), (
        f"/search {params} returns an object with an items list"
    )
    assert (body.get("page"), body.get("page_size")) == (page, page_size), (
        f"/search {params} reports page={page} and page_size={page_size}, "
        f"got page={body.get('page')!r} page_size={body.get('page_size')!r}"
    )
    for item in body["items"]:
        bad = [k for k, t in ITEM_TYPES.items()
               if not isinstance(item.get(k), t) or isinstance(item.get(k), bool)]
        assert not bad, f"every result has the documented product fields; wrong or missing {bad}"
    return body["items"]


# --- Required ----------------------------------------------------------------


def catalog_ingestion(snapshot: dict) -> None:
    """The Product collection contains every catalog product exactly once."""
    stored = [o["properties"] for o in snapshot["objects"][COLLECTION]]
    catalog = snapshot["fixture"]
    assert len(stored) == len(catalog), (
        f"{COLLECTION} holds {len(catalog)} objects, one per catalog product; got {len(stored)}"
    )
    # Stored objects may carry extra properties; compare only catalog fields.
    unmatched = [p["sku"] for p in catalog
                 if sum(p.items() <= o.items() for o in stored) != 1]
    assert not unmatched, f"each catalog product is stored exactly once; not so for {unmatched}"


def product_schema(snapshot: dict) -> None:
    """sku, name, description, and category are text properties; price is number."""
    actual = {name: p["dataType"][0] for name, p in properties(snapshot).items()}
    wrong = {k: actual.get(k) for k, t in PROPERTY_TYPES.items() if actual.get(k) != t}
    assert not wrong, f"{COLLECTION} property data types match {PROPERTY_TYPES}; differing: {wrong}"


def weaviate_managed_vectorization(snapshot: dict) -> str:
    """Product uses a named vector with text2vec-ollama or text2vec-transformers,
    and every object has a generated vector."""
    config = collection(snapshot)
    named = {
        name: next(iter(vector.get("vectorizer") or {"none": None}))
        for name, vector in (config.get("vectorConfig") or {}).items()
    }
    legacy = config.get("vectorizer", "none")
    assert named or legacy == "none", (
        f"{COLLECTION} configures vectorization as a named vector; it uses the legacy "
        f"collection-level vectorizer ({legacy}) instead"
    )
    assert named and set(named.values()) <= LOCAL_VECTORIZERS, (
        f"{COLLECTION} has a named vector using {' or '.join(sorted(LOCAL_VECTORIZERS))}; "
        f"named vectors: {named or 'none'}"
    )
    missing = [o["id"] for o in snapshot["objects"][COLLECTION] if not o["has_vector"]]
    assert not missing, f"every {COLLECTION} object has a vector; {len(missing)} do not"
    return f"named vectors: {named}"


def search_contract(snapshot: dict) -> None:
    """/search rejects invalid parameters with 4xx and returns the documented
    pagination metadata, item shape, and default page size."""
    for label, probe in snapshot["probes"].items():
        if label == "missing-query" or label.startswith("invalid-"):
            assert 400 <= probe["status"] < 500, (
                f"/search rejects {probe['params']} with a 4xx status, got {probe['status']}"
            )
    default = items(snapshot, "default-page")
    assert len(default) == DEFAULT_PAGE_SIZE, (
        f"/search without page_size returns {DEFAULT_PAGE_SIZE} items, got {len(default)}"
    )


def exact_sku_retrieval(snapshot: dict) -> None:
    """An exact SKU query ranks the matching product first."""
    found = [i["sku"] for i in items(snapshot, "exact-sku")]
    assert found[:1] == [EXACT_SKU], f"query {EXACT_SKU!r} ranks it first; got {found}"


def semantic_retrieval(snapshot: dict) -> None:
    """A natural-language query returns the product matching its meaning."""
    found = [i["sku"] for i in items(snapshot, "semantic")]
    assert SEMANTIC_SKU in found, (
        f"query 'soggy mountaineering trek' returns {SEMANTIC_SKU} on page 1; got {found}"
    )


def pagination(snapshot: dict) -> None:
    """Pages are stable, do not overlap, and concatenate to the larger request's order."""
    pages = [items(snapshot, f"pagination-page-{n}") for n in range(1, PAGINATION_PAGES + 1)]
    assert items(snapshot, "pagination-page-1-repeat") == pages[0], (
        "repeating a page returns the same results"
    )
    skus = [i["sku"] for page in pages for i in page]
    assert len(skus) == len(set(skus)), "pages do not contain overlapping products"
    # Truncate to the requested window, not the reference's observed length, so
    # a short reference cannot hide extra results.
    combined = [i for page in pages for i in page][:PAGINATION_REFERENCE_SIZE]
    assert combined == items(snapshot, "pagination-reference"), (
        "concatenated page_size=5 pages match one page_size=24 request in order"
    )


# --- Preferred ---------------------------------------------------------------


def sku_category_field_tokenization(snapshot: dict) -> None:
    """sku and category use field tokenization."""
    actual = {k: properties(snapshot).get(k, {}).get("tokenization") for k in ("sku", "category")}
    assert actual == {"sku": "field", "category": "field"}, (
        f"sku and category use field tokenization; got {actual}"
    )


def hybrid_query(snapshot: dict) -> None:
    """The submitted code calls collection.query.hybrid(...)."""
    # Trade-off: a substring match over submitted files, not weval4's check that
    # the /search route itself makes the call.
    callers = [name for name, text in snapshot["files"].items()
               if name.endswith(".py") and ".query.hybrid(" in text]
    assert callers, "submitted Python code calls .query.hybrid(...)"


REQUIRED = [
    catalog_ingestion,
    product_schema,
    weaviate_managed_vectorization,
    search_contract,
    exact_sku_retrieval,
    semantic_retrieval,
    pagination,
]
PREFERRED = [sku_category_field_tokenization, hybrid_query]
