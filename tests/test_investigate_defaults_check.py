"""Calibrate investigate-defaults checks: the Oracle snapshot passes, and each
broken audit fails exactly the check aimed at it, for the stated reason.

``fixtures/investigate-defaults-oracle-snapshot.json`` is a real snapshot
retained from a Modal Oracle Trial.
"""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from weval.verify import score

ROOT = Path(__file__).parents[1]
ORACLE = json.loads((ROOT / "tests/fixtures/investigate-defaults-oracle-snapshot.json").read_text())

_spec = importlib.util.spec_from_file_location(
    "investigate_defaults_check", ROOT / "tasks/investigate-defaults/check.py"
)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def failures(snapshot: dict) -> dict[str, str]:
    return {r["name"]: r["notes"] for r in score(check, snapshot) if not r["passed"]}


def with_audit(**fields: object) -> dict:
    snapshot = copy.deepcopy(ORACLE)
    snapshot["audit"]["parsed"].update(fields)
    return snapshot


def test_oracle_passes_every_check():
    assert failures(ORACLE) == {}


@pytest.mark.parametrize(
    ("fields", "failing_check", "reason"),
    [
        ({"server_version": "1.24.0"}, "version-reported-truthfully", "reported '1.24.0'"),
        # An agent that reads only the Compose file, which enables no modules.
        ({"vectorizer_modules": []}, "vectorizer-modules-reported-truthfully",
         "missing ['text2vec-aws'"),
        ({"vectorizer_modules": ORACLE["audit"]["parsed"]["vectorizer_modules"]
          + ["text2vec-contextionary"]},
         "vectorizer-modules-reported-truthfully",
         "not listed by the server ['text2vec-contextionary']"),
        ({"vectorizer_modules": ORACLE["audit"]["parsed"]["vectorizer_modules"]
          + ["generative-openai"]},
         "vectorizer-modules-reported-truthfully", "not vectorizers ['generative-openai']"),
        ({"default_vectorizer": "text2vec-openai"}, "default-vectorizer-reported-truthfully",
         "live default (none)"),
        ({"anonymous_access": False}, "auth-reported-truthfully", "reported False"),
    ],
)
def test_broken_audit_fails_only_its_check(fields, failing_check, reason):
    failed = failures(with_audit(**fields))
    assert list(failed) == [failing_check]
    assert reason in failed[failing_check]


def test_none_string_reports_no_default_vectorizer():
    assert failures(with_audit(default_vectorizer="none")) == {}


def test_missing_audit_fails_every_check_with_the_reason():
    snapshot = copy.deepcopy(ORACLE)
    snapshot["audit"] = {"raw": None, "parsed": None, "error": "/app/audit.json does not exist"}
    failed = failures(snapshot)
    assert len(failed) == len(check.REQUIRED)
    assert all("does not exist" in notes for notes in failed.values())


def test_failed_snapshot_fails_every_check_without_crashing():
    results = score(check, {"error": "Traceback: weaviate unreachable"})
    assert results and not any(r["passed"] for r in results)
    assert all("snapshot failed" in r["notes"] for r in results)
