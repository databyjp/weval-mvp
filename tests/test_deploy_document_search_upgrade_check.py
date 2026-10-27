"""Calibrate deploy/document-search-upgrade checks: the Oracle snapshot passes, and each broken
variant fails exactly the check aimed at it, for the stated reason.

``fixtures/deploy-document-search-upgrade-oracle-snapshot.json`` is a real snapshot retained from a
Modal Oracle Trial. The starting stack is Weaviate 1.30.16 with
weaviate-client 4.12.1.
"""

import copy
import json
import uuid

import pytest
from conftest import ROOT, failures, load_module

ORACLE = json.loads(
    (
        ROOT / "tests/fixtures/deploy-document-search-upgrade-oracle-snapshot.json"
    ).read_text()
)
check = load_module(ROOT / "tasks/deploy/document-search-upgrade/check.py")


def server_not_upgraded(s: dict) -> None:
    s["weaviate_version"] = "1.30.16"


def requirements_not_updated(s: dict) -> None:
    # The client was upgraded in the environment but the pin was left behind.
    s["files"]["requirements.txt"] = s["files"]["requirements.txt"].replace(
        "weaviate-client==4.23.1", "weaviate-client==4.12.1"
    )


def reimported_with_new_uuids(s: dict) -> None:
    for o in s["objects"]["DocumentChunk"]:
        o["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, o["id"]))


def recreated_with_default_tokenization(s: dict) -> None:
    for prop in s["schema"]["properties"]:
        if prop["name"] == "document_id":
            prop["tokenization"] = "word"


def search_returns_server_error(s: dict) -> None:
    for probe in s["probes"].values():
        probe["status"], probe["body"] = 500, "Internal Server Error"


def inference_service_removed(s: dict) -> None:
    s["vector_probe"].update(
        create_status=500, dimensions=None, finite_numbers=False, nonzero=False
    )


def test_oracle_passes_every_check():
    assert failures(check, ORACLE) == {}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_check", "reason"),
    [
        (server_not_upgraded, "server-version", "running 1.30.16"),
        (
            requirements_not_updated,
            "client-version",
            "declares ['weaviate-client==4.12.1']",
        ),
        (reimported_with_new_uuids, "document-preservation", "500 differ"),
        (
            recreated_with_default_tokenization,
            "collection-definition",
            "'properties.document_id': [['text'], 'word', True]",
        ),
        (search_returns_server_error, "search-contract", "got 500"),
        (
            inference_service_removed,
            "vectorizer-availability",
            "can be inserted; got 500",
        ),
    ],
)
def test_broken_variant_fails_only_its_check(break_snapshot, failing_check, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(check, snapshot)
    assert list(failed) == [failing_check]
    assert reason in failed[failing_check]
