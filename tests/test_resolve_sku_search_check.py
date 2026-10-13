"""Calibrate resolve-sku-search checks: the Oracle snapshot passes, and each
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
    "resolve_sku_search_check", ROOT / "tasks/resolve-sku-search/check.py"
)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def results(snapshot: dict) -> dict[str, dict]:
    return {r["name"]: r for r in score(check, snapshot)}


def failures(snapshot: dict) -> dict[str, str]:
    return {name: r["notes"] for name, r in results(snapshot).items() if not r["passed"]}


def schema_property(s: dict, name: str) -> dict:
    return next(p for p in s["schema"]["properties"] if p["name"] == name)


def word_tokenized_ranking(s: dict) -> None:
    # The seeded baseline's /search order, observed in the local dry run.
    by_sku = {p["sku"]: p for p in s["catalog"]}
    s["probes"]["exact-sku"]["body"]["items"] = [
        by_sku[sku] for sku in ("9917-ZXQ", "ZXQ-9917", "ZXQ-9917-W")
    ]


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
        (word_tokenized_ranking, "exact-sku-retrieval", "got ['9917-ZXQ', 'ZXQ-9917'"),
        (exact_match_only_search, "search-contract", "returns TRAIL-001"),
        (dropped_catalog, "document-preservation", "holds 26 objects"),
        (price_as_text, "collection-schema", "'price': 'text'"),
        (name_field_tokenization, "collection-schema", "changed: {'name': 'field'}"),
        (app_side_workaround, "sku-field-tokenization", "got 'word'"),
    ],
)
def test_broken_variant_fails_only_its_check(break_snapshot, failing_check, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(snapshot)
    assert list(failed) == [failing_check]
    assert reason in failed[failing_check]


def test_reingest_with_new_uuids_passes_and_is_recorded():
    snapshot = copy.deepcopy(ORACLE)
    for n, obj in enumerate(snapshot["objects"]):
        obj["id"] = f"00000000-0000-4000-8000-{n:012d}"
    preservation = results(snapshot)["document-preservation"]
    assert preservation["passed"]
    assert preservation["notes"] == "UUIDs preserved: 0/26"


def test_failed_snapshot_fails_every_check_without_crashing():
    results = score(check, {"error": "Traceback: weaviate unreachable"})
    assert results and not any(r["passed"] for r in results)
    assert all("snapshot failed" in r["notes"] for r in results)
