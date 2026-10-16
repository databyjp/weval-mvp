"""Calibrate investigate/current-practices checks: the Oracle snapshot passes,
and each broken variant fails exactly the check aimed at it, for the stated reason.

``fixtures/investigate-current-practices-oracle-snapshot.json`` is a real
snapshot retained from a local Oracle Trial.
"""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from weval.verify import score

ROOT = Path(__file__).parents[1]
ORACLE = json.loads((ROOT / "tests/fixtures/investigate-current-practices-oracle-snapshot.json").read_text())

_spec = importlib.util.spec_from_file_location(
    "investigate_current_practices_check", ROOT / "tasks/investigate/current-practices/check.py"
)
assert _spec and _spec.loader
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def failures(snapshot: dict) -> dict[str, str]:
    return {r["name"]: r["notes"] for r in score(check, snapshot) if not r["passed"]}


def missing_file(s: dict) -> None:
    s["findings"] = {"text": None, "parsed": None, "error": "/app/findings.json does not exist"}


def missing_item(s: dict) -> None:
    del s["findings"]["parsed"]["search"]


def answer_not_string(s: dict) -> None:
    s["findings"]["parsed"]["indexing"]["answer"] = {"index": "hnsw", "quantization": "rq"}


def test_oracle_passes_every_check():
    assert failures(ORACLE) == {}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_check", "reason"),
    [
        (missing_file, "findings-file", "does not exist"),
        (missing_item, "findings-file", "missing ['search']"),
        (answer_not_string, "findings-file", "malformed ['indexing']"),
    ],
)
def test_broken_variant_fails_only_its_check(break_snapshot, failing_check, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(snapshot)
    assert list(failed) == [failing_check]
    assert reason in failed[failing_check]
