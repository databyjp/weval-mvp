"""Calibrate build/ecommerce-search checks: the Oracle snapshot passes, and each broken
variant fails exactly the check aimed at it, for the stated reason.

``fixtures/build-ecommerce-search-oracle-snapshot.json`` is a real snapshot retained from a
Modal Oracle Trial.
"""

import copy
import json

import pytest
from conftest import ROOT, failures, load_module

ORACLE = json.loads(
    (ROOT / "tests/fixtures/build-ecommerce-search-oracle-snapshot.json").read_text()
)
check = load_module(ROOT / "tasks/build/ecommerce-search/check.py")


def product_class(snapshot: dict) -> dict:
    return next(c for c in snapshot["schema"]["classes"] if c["class"] == "Product")


def legacy_vectorizer(s: dict) -> None:
    product_class(s).pop("vectorConfig", None)
    product_class(s)["vectorizer"] = "text2vec-transformers"


def missing_product(s: dict) -> None:
    s["objects"]["Product"] = [
        o for o in s["objects"]["Product"] if o["properties"]["sku"] != "ZXQ-9917"
    ]


def word_tokenization(s: dict) -> None:
    for prop in product_class(s)["properties"]:
        if prop["name"] == "sku":
            prop["tokenization"] = "word"


def near_text_search(s: dict) -> None:
    s["files"] = {
        k: v.replace(".query.hybrid(", ".query.near_text(")
        for k, v in s["files"].items()
    }


def default_page_size_10(s: dict) -> None:
    body = s["probes"]["default-page"]["body"]
    body["page_size"] = 10
    body["items"] = body["items"] * 2


def test_oracle_passes_every_check():
    assert failures(check, ORACLE) == {}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_check", "reason"),
    [
        (
            legacy_vectorizer,
            "weaviate-managed-vectorization",
            "legacy collection-level vectorizer",
        ),
        (missing_product, "catalog-ingestion", "holds 24 objects"),
        (word_tokenization, "sku-category-field-tokenization", "'sku': 'word'"),
        (near_text_search, "hybrid-query", "it calls .query.near_text(...)"),
        (default_page_size_10, "search-contract", "page_size=5"),
    ],
)
def test_broken_variant_fails_only_its_check(break_snapshot, failing_check, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(check, snapshot)
    assert list(failed) == [failing_check]
    assert reason in failed[failing_check]
