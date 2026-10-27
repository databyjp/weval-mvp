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
    s["findings"]["parsed"]["config_ingestion"]["answer"] = {"index": "hnsw", "quantization": "rq"}


def server_patch_behind(s: dict) -> None:
    s["findings"]["parsed"]["weaviate_version"]["answer"] = "v1.40.1, the latest 1.40 release in the docs"


def server_minor_only(s: dict) -> None:
    s["findings"]["parsed"]["weaviate_version"]["answer"] = "Weaviate 1.40"


def server_version_prefix(s: dict) -> None:
    s["latest_releases"]["weaviate"]["version"] = "1.40.20"


def server_release_unavailable(s: dict) -> None:
    s["latest_releases"]["weaviate"] = {
        "version": None, "source": None, "status": 403, "error": "API: rate limit exceeded; feed: 503",
    }


def client_version_behind(s: dict) -> None:
    s["findings"]["parsed"]["client_library_versions"]["answer"] = "Python weaviate-client 4.22.0"


def legacy_vectorizer_config(s: dict) -> None:
    s["findings"]["parsed"]["config_ingestion"]["answer"] = (
        "Create the collection with vectorizer_config=Configure.Vectorizer.text2vec_openai(); "
        "import with client-side batching."
    )


def prose_without_api(s: dict) -> None:
    s["findings"]["parsed"]["config_ingestion"]["answer"] = (
        "Define the collection up front with a vectorizer and properties; import with batching."
    )


def uncited_answer(s: dict) -> None:
    s["findings"]["parsed"]["search"]["sources"] = []


def blog_source(s: dict) -> None:
    s["findings"]["parsed"]["search"]["sources"].append("https://medium.com/some-weaviate-post")


def test_oracle_passes_every_check():
    assert failures(ORACLE) == {}


def test_versions_match_with_a_v_prefix_and_trailing_punctuation():
    snapshot = copy.deepcopy(ORACLE)
    snapshot["findings"]["parsed"]["weaviate_version"]["answer"] = "Use v1.40.2."
    assert failures(snapshot) == {}


def test_missing_file_fails_every_check():
    snapshot = copy.deepcopy(ORACLE)
    missing_file(snapshot)
    assert set(failures(snapshot)) == {r["name"] for r in score(check, snapshot)}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_checks", "reason"),
    [
        (missing_item, ["findings-file"], "missing ['search']"),
        # The malformed answer also cannot be searched for the vector API.
        (answer_not_string, ["findings-file", "current-vector-config"], "malformed ['config_ingestion']"),
        (server_patch_behind, ["weaviate-version-latest"], "names the latest release 1.40.2"),
        (server_minor_only, ["weaviate-version-latest"], "names the latest release 1.40.2"),
        (server_version_prefix, ["weaviate-version-latest"], "names the latest release 1.40.20"),
        (server_release_unavailable, ["weaviate-version-latest"], "rate limit exceeded"),
        (client_version_behind, ["python-client-version-latest"], "latest Python client release 4.24.1"),
        (legacy_vectorizer_config, ["current-vector-config"], "Configure.Vectorizer"),
        (prose_without_api, ["current-vector-config"], "names vector_config"),
        (uncited_answer, ["canonical-sources"], "uncited ['search']"),
        (blog_source, ["canonical-sources"], "non-canonical ['https://medium.com/some-weaviate-post']"),
    ],
)
def test_broken_variant_fails_only_its_checks(break_snapshot, failing_checks, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(snapshot)
    assert list(failed) == failing_checks
    assert reason in failed[failing_checks[0]]
