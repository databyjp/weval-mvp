"""Calibrate investigate/client-code-examples checks: the Oracle snapshot
passes, and each broken variant fails exactly the checks aimed at it, for the
stated reason.

``fixtures/investigate-client-code-examples-oracle-snapshot.json`` is a real
snapshot retained from a local Oracle Trial.
"""

import copy
import json

import pytest
from conftest import ROOT, failures, load_module

from weval.verify import score

ORACLE = json.loads(
    (
        ROOT / "tests/fixtures/investigate-client-code-examples-oracle-snapshot.json"
    ).read_text()
)
check = load_module(ROOT / "tasks/investigate/client-code-examples/check.py")


def code(s: dict, item: str) -> dict:
    return s["findings"]["parsed"][item]["code"]


def missing_file(s: dict) -> None:
    s["findings"] = {
        "text": None,
        "parsed": None,
        "error": "/app/findings.json does not exist",
    }


def missing_item(s: dict) -> None:
    del s["findings"]["parsed"]["deployment"]


def missing_language(s: dict) -> None:
    del code(s, "config_ingestion")["typescript"]


def test_oracle_passes_every_check():
    assert failures(check, ORACLE) == {}


def test_missing_file_fails_every_check():
    snapshot = copy.deepcopy(ORACLE)
    missing_file(snapshot)
    assert set(failures(check, snapshot)) == {r["name"] for r in score(check, snapshot)}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_checks", "reason"),
    [
        (missing_item, ["findings-file"], "missing ['deployment']"),
        (missing_language, ["findings-file"], "malformed ['config_ingestion']"),
    ],
)
def test_broken_variant_fails_only_its_checks(break_snapshot, failing_checks, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(check, snapshot)
    assert list(failed) == failing_checks
    assert reason in failed[failing_checks[0]]
