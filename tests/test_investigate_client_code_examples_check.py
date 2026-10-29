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


def python_legacy_vectorizer(s: dict) -> None:
    code(s, "config_ingestion")["python"] = (
        'client.collections.create("Article", '
        "vectorizer_config=Configure.Vectorizer.text2vec_openai())"
    )


def typescript_legacy_vectorizer(s: dict) -> None:
    code(s, "config_ingestion")["typescript"] = (
        "await client.collections.create({ name: 'Article', "
        "vectorizers: weaviate.configure.vectorizer.text2VecOpenAI() })"
    )


def go_v5_client(s: dict) -> None:
    code(s, "config_ingestion")["go"] = (
        "err := client.Schema().ClassCreator().WithClass(&models.Class{"
        'Class: "Article", Vectorizer: "text2vec-openai"}).Do(ctx)'
    )


def go_mixed_clients(s: dict) -> None:
    # A v6 collection with the manual batcher from the v5 tab beside it, which
    # the docs offer because v5 has no server-side batching.
    code(s, "config_ingestion")["go"] = (
        "_, err := client.Collections.Create(ctx, collections.Collection{"
        'Name: "Article"})\n'
        "batcher := client.Batch().ObjectsBatcher()"
    )


def go_rest_calls(s: dict) -> None:
    code(s, "search")["go"] = (
        'resp, err := http.Post("http://localhost:8080/v1/graphql", '
        '"application/json", body)'
    )


def typescript_vector_search(s: dict) -> None:
    code(s, "search")["typescript"] = (
        "const result = await articles.query.nearText('food', { limit: 3 })"
    )


def test_oracle_passes_every_check():
    assert failures(check, ORACLE) == {}


def test_legacy_api_named_as_replaced_passes():
    snapshot = copy.deepcopy(ORACLE)
    code(snapshot, "config_ingestion")["python"] += (
        "# vector_config replaces the legacy vectorizer_config=Configure.Vectorizer\n"
    )
    assert failures(check, snapshot) == {}


def test_configure_vectors_spelling_passes():
    snapshot = copy.deepcopy(ORACLE)
    code(snapshot, "config_ingestion")["typescript"] = (
        "await client.collections.create({ name: 'Article', "
        "vectorizers: weaviate.configure.vectors.text2VecOpenAI() })"
    )
    assert failures(check, snapshot) == {}


def test_missing_file_fails_every_check():
    snapshot = copy.deepcopy(ORACLE)
    missing_file(snapshot)
    assert set(failures(check, snapshot)) == {r["name"] for r in score(check, snapshot)}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_checks", "reason"),
    [
        (missing_item, ["findings-file"], "missing ['deployment']"),
        # The missing snippet also cannot be searched for the vector API.
        (
            missing_language,
            ["findings-file", "typescript-current-vector-config"],
            "malformed ['config_ingestion']",
        ),
        (
            python_legacy_vectorizer,
            ["python-current-vector-config"],
            "uses vector_config=Configure.Vectors",
        ),
        (
            typescript_legacy_vectorizer,
            ["typescript-current-vector-config"],
            "uses vectors.<module>()",
        ),
        (go_v5_client, ["go-v6-client"], "v5 call .Schema()"),
        (go_mixed_clients, ["go-v6-client"], "ObjectsBatcher"),
        (
            go_rest_calls,
            ["go-v6-client", "hybrid-search-code"],
            "no v6 collections API",
        ),
        (typescript_vector_search, ["hybrid-search-code"], "not in ['typescript']"),
    ],
)
def test_broken_variant_fails_only_its_checks(break_snapshot, failing_checks, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(check, snapshot)
    assert list(failed) == failing_checks
    assert reason in failed[failing_checks[0]]
