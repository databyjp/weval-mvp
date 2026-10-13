"""Calibrate build-spin-up checks: the Oracle snapshot passes, and each broken
variant fails exactly the check aimed at it, for the stated reason.

``fixtures/build-spin-up-oracle-snapshot.json`` is a real snapshot retained
from a Modal Oracle Trial.
"""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from weval.verify import score

ROOT = Path(__file__).parents[1]
ORACLE = json.loads((ROOT / "tests/fixtures/build-spin-up-oracle-snapshot.json").read_text())

_spec = importlib.util.spec_from_file_location(
    "build_spin_up_check", ROOT / "tasks/build-spin-up/check.py"
)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def results(snapshot: dict) -> dict[str, dict]:
    return {r["name"]: r for r in score(check, snapshot)}


def failures(snapshot: dict) -> dict[str, str]:
    return {name: r["notes"] for name, r in results(snapshot).items() if not r["passed"]}


def not_ready(s: dict) -> None:
    s["ready_status"] = 503


def old_server(s: dict) -> None:
    s["meta"]["version"] = "1.27.0"


def no_vectorizer(s: dict) -> None:
    s["collection"]["vectorConfig"] = {"default": {"vectorizer": {"none": {}}}}


def api_key_vectorizer(s: dict) -> None:
    # Observed locally with a collection-level text2vec-openai and no OpenAI key.
    s["vector_probe"] = {
        "create_status": 500,
        "create_body": {"error": [{"message": "API Key: no api key found"}]},
        "vectors": {},
        "delete_status": 404,
    }


def no_data_mount(s: dict) -> None:
    s["container"]["mounts"] = []


def test_oracle_passes_every_check():
    assert failures(ORACLE) == {}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_check", "reason"),
    [
        (not_ready, "weaviate-ready", "got 503"),
        (old_server, "server-version", "running 1.27.0"),
        (no_vectorizer, "collection-vectorizer", "configures a vectorizer module"),
        (api_key_vectorizer, "vectorizer-availability", "no api key found"),
        (no_data_mount, "persistence-configured", "covers the data path /var/lib/weaviate"),
    ],
)
def test_broken_variant_fails_only_its_check(break_snapshot, failing_check, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(snapshot)
    assert list(failed) == [failing_check]
    assert reason in failed[failing_check]


def test_auth_posture_records_refused_anonymous_access():
    snapshot = copy.deepcopy(ORACLE)
    snapshot["auth"] = {"anonymous_status": 401, "api_key_count": 1, "used_api_key": True}
    posture = results(snapshot)["auth-posture"]
    assert posture["passed"]
    assert posture["notes"] == "anonymous /v1/schema: refused; API keys: 1"


def test_failed_snapshot_fails_every_check_without_crashing():
    results = score(check, {"error": "Traceback: weaviate unreachable"})
    assert results and not any(r["passed"] for r in results)
    assert all("snapshot failed" in r["notes"] for r in results)
