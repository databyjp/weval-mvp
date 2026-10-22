"""Calibrate resolve/sku-search checks: the Oracle snapshot passes, and each
broken variant fails exactly the check aimed at it, for the stated reason.

``fixtures/resolve-sku-search-oracle-snapshot.json`` is a real snapshot
retained from a Modal Oracle Trial, which migrated Product behind an alias.
"""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from weval.verify import score

ROOT = Path(__file__).parents[1]
ORACLE = json.loads((ROOT / "tests/fixtures/resolve-sku-search-oracle-snapshot.json").read_text())

_spec = importlib.util.spec_from_file_location(
    "resolve_sku_search_check", ROOT / "tasks/resolve/sku-search/check.py"
)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def results(snapshot: dict) -> dict[str, dict]:
    return {r["name"]: r for r in score(check, snapshot)}


def failures(snapshot: dict) -> dict[str, str]:
    return {name: r["notes"] for name, r in results(snapshot).items() if not r["passed"]}


def schema_property(s: dict, name: str) -> dict:
    return next(p for p in s["schema"]["properties"] if p["name"] == name)


def set_ranking(s: dict, query: str, skus: tuple[str, ...]) -> None:
    by_sku = {p["sku"]: p for p in s["catalog"]}
    s["probes"][f"exact-sku-{query}"]["body"]["items"] = [by_sku[sku] for sku in skus]


def word_tokenized_ranking(s: dict) -> None:
    # The seeded baseline's /search order, observed in the local dry run.
    for query in ("ZXQ-9917", "9917@ZXQ"):
        set_ranking(s, query, ("9917-ZXQ", "ZXQ-9917", "9917@ZXQ", "ZXQ-4831", "AQ1-9917"))


def hoisted_filter_matches(s: dict) -> None:
    # HrrRY7G's workaround: word-tokenized equal() matches, in seed order, ahead of BM25.
    for query in ("9917-ZXQ", "9917@ZXQ"):
        set_ranking(s, query, ("ZXQ-9917", "9917@ZXQ", "9917-ZXQ", "ZXQ-4831", "AQ1-9917"))


def lowercase_tokenized_ranking(s: dict) -> None:
    # Lowercase tokenization stores ZXQ-9917 and zxq-9917 as the same token, so
    # both queries return the same order.
    for query in ("ZXQ-9917", "zxq-9917"):
        set_ranking(s, query, ("ZXQ-9917", "zxq-9917"))


def whitespace_tokenized_ranking(s: dict) -> None:
    # Whitespace tokenization splits ZXQ 9917 and 9917 ZXQ into the same tokens.
    for query in ("ZXQ 9917", "9917 ZXQ"):
        set_ranking(s, query, ("ZXQ 9917", "9917 ZXQ"))


def exact_match_only_search(s: dict) -> None:
    s["probes"]["keyword"]["body"]["items"] = []


def dropped_catalog(s: dict) -> None:
    s["objects"] = []


def price_as_text(s: dict) -> None:
    schema_property(s, "price")["dataType"] = ["text"]


def name_field_tokenization(s: dict) -> None:
    schema_property(s, "name")["tokenization"] = "field"


def app_side_workaround(s: dict) -> None:
    schema_property(s, "sku")["tokenization"] = "word"


def test_oracle_passes_every_check():
    assert failures(ORACLE) == {}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_check", "reason"),
    [
        (word_tokenized_ranking, "exact-sku-retrieval", "'ZXQ-9917': ['9917-ZXQ'"),
        (hoisted_filter_matches, "exact-sku-retrieval", "'9917-ZXQ': ['ZXQ-9917'"),
        (lowercase_tokenized_ranking, "exact-sku-retrieval", "'zxq-9917': ['ZXQ-9917'"),
        (whitespace_tokenized_ranking, "exact-sku-retrieval", "'9917 ZXQ': ['ZXQ 9917'"),
        (exact_match_only_search, "search-contract", "returns TRAIL-001"),
        (dropped_catalog, "document-preservation", "holds 31 objects"),
        (price_as_text, "collection-definition", "'price': 'text'"),
        (name_field_tokenization, "other-properties-word-tokenization", "changed: {'name': 'field'}"),
        (app_side_workaround, "sku-field-tokenization", "got 'word'"),
    ],
)
def test_broken_variant_fails_only_its_check(break_snapshot, failing_check, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(snapshot)
    assert list(failed) == [failing_check]
    assert reason in failed[failing_check]
