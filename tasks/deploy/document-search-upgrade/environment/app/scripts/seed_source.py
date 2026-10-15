"""Seed the evaluator's pre-existing document collection before agent execution.

The baseline is stored outside /app so edits to the submitted workspace cannot
silently change what the verifier expects to survive the upgrade.
"""

import importlib.metadata
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

_COLLECTION = "DocumentChunk"
_NAMESPACE = UUID("498a303c-14d8-4a0c-b506-3219ec232954")
_BASE_URL = f"http://{os.environ.get('WEAVIATE_HTTP_HOST', 'weaviate')}:{os.environ.get('WEAVIATE_HTTP_PORT', '8080')}"
_BASELINE_PATH = Path("/logs/verifier/baseline.json")
_TOPICS = (
    ("trail running", "Trail running shoes need grip on wet stone and uneven paths."),
    (
        "home solar",
        "Solar panels produce electricity and an inverter connects them to the home.",
    ),
    (
        "garden soil",
        "Compost improves garden soil and helps vegetable roots retain moisture.",
    ),
    (
        "coffee brewing",
        "Coffee extraction depends on grind size, water temperature, and brew time.",
    ),
    (
        "bike repair",
        "Bicycle brake pads need clearance from the rim and careful cable tension.",
    ),
    (
        "network security",
        "Network firewalls filter traffic according to explicit access rules.",
    ),
    (
        "flight planning",
        "Flight plans account for weather, fuel reserves, and airport approach procedures.",
    ),
    (
        "marine biology",
        "Coral reefs support marine fish and depend on clear, warm water.",
    ),
    (
        "bread baking",
        "Bread dough rises when yeast ferments sugars and produces carbon dioxide.",
    ),
    (
        "data backup",
        "Backups protect files against accidental deletion and hardware failure.",
    ),
    (
        "mountain hiking",
        "Hikers carry water and check trail conditions before climbing.",
    ),
    (
        "electric vehicles",
        "Electric cars recharge batteries through a compatible charging station.",
    ),
    (
        "public libraries",
        "Libraries lend books and provide searchable catalogs to readers.",
    ),
    (
        "wildlife conservation",
        "Wildlife corridors connect habitats for migrating animals.",
    ),
    (
        "water treatment",
        "Water filters remove sediment before drinking water is disinfected.",
    ),
    (
        "astronomy",
        "Astronomers observe distant galaxies with optical and radio telescopes.",
    ),
    (
        "music production",
        "Recording engineers mix audio tracks and balance their volume.",
    ),
    (
        "urban transit",
        "Transit schedules coordinate bus arrivals with passenger connections.",
    ),
    (
        "medical research",
        "Clinical trials measure treatment outcomes against a control group.",
    ),
    (
        "ocean navigation",
        "Sailors use charts, tides, and bearings to navigate coastal waters.",
    ),
    (
        "forest ecology",
        "Forest canopies shelter plants and regulate light on the ground.",
    ),
    (
        "language learning",
        "Vocabulary practice and conversation improve language fluency.",
    ),
    (
        "space exploration",
        "Spacecraft use orbital trajectories to reach distant planets.",
    ),
    ("food safety", "Refrigeration limits bacterial growth in perishable foods."),
    (
        "building insulation",
        "Insulation reduces heat transfer through walls and ceilings.",
    ),
)


def source_objects() -> list[dict[str, Any]]:
    """Return the same 500 identified chunks for each fresh Trial."""
    return [
        {
            "id": str(uuid5(_NAMESPACE, f"{document_number}:{chunk_index}")),
            "properties": {
                "document_id": f"DOC-{document_number:03d}",
                "chunk_index": chunk_index,
                "title": title,
                "text": f"{paragraph} Section {chunk_index + 1} of the {title} guide.",
            },
        }
        for document_number, (title, paragraph) in enumerate(_TOPICS, start=1)
        for chunk_index in range(20)
    ]


def source_schema() -> dict[str, Any]:
    """Define the legacy single-vector collection before the upgrade."""
    return {
        "class": _COLLECTION,
        "vectorizer": "text2vec-transformers",
        "vectorIndexType": "hnsw",
        "moduleConfig": {"text2vec-transformers": {"vectorizeClassName": False}},
        "properties": [
            {
                "name": "document_id",
                "dataType": ["text"],
                "tokenization": "field",
                "moduleConfig": {"text2vec-transformers": {"skip": True}},
            },
            {"name": "chunk_index", "dataType": ["int"]},
            {"name": "title", "dataType": ["text"]},
            {"name": "text", "dataType": ["text"]},
        ],
    }


def _request(path: str, *, payload: object | None = None) -> Any:
    """Send a source-database request and return its decoded JSON body.

    A missing payload selects GET; a payload selects POST with a JSON body.

    Raises:
        RuntimeError: The configured URL is not HTTP or the response is not
            valid JSON.
    """
    body = None if payload is None else json.dumps(payload).encode()
    url = _BASE_URL + path
    if urllib.parse.urlsplit(url).scheme != "http":
        raise RuntimeError("source database must use HTTP on its Trial network")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        try:
            return json.load(response)
        except json.JSONDecodeError as error:
            raise RuntimeError("source database returned invalid JSON") from error


def seed() -> None:
    """Create and authenticate the pre-agent source collection.

    The evaluator verifies its server and client versions, requires an empty
    volume, imports the deterministic corpus, waits for all objects and vectors,
    then writes the baseline used by the Task verifier.

    Raises:
        RuntimeError: Evaluator versions, initial state, import results, object
            count, or generated vectors violate the baseline contract.
    """
    if _request("/v1/meta")["version"] != "1.30.16":
        raise RuntimeError("evaluator source database has the wrong version")
    if importlib.metadata.version("weaviate-client") != "4.12.1":
        raise RuntimeError("evaluator source Python client has the wrong version")
    try:
        _request(f"/v1/schema/{_COLLECTION}")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    else:
        raise RuntimeError("source volume is not empty before Trial initialization")

    objects = source_objects()
    _request("/v1/schema", payload=source_schema())
    for start in range(0, len(objects), 25):
        batch = _request(
            "/v1/batch/objects",
            payload={
                "objects": [
                    {"class": _COLLECTION, **obj} for obj in objects[start : start + 25]
                ]
            },
        )
        if len(batch) != len(objects[start : start + 25]) or any(
            entry.get("result", {}).get("status") != "SUCCESS" for entry in batch
        ):
            raise RuntimeError("source batch import failed")

    for _ in range(60):
        count = _request(
            "/v1/graphql",
            payload={"query": "{ Aggregate { DocumentChunk { meta { count } } } }"},
        )["data"]["Aggregate"][_COLLECTION][0]["meta"]["count"]
        if count == len(objects):
            break
        time.sleep(2)
    else:
        raise RuntimeError("source collection did not reach 500 objects")

    source_vector = _request(
        f"/v1/objects/{_COLLECTION}/{objects[0]['id']}?include=vector"
    )["vector"]
    if not isinstance(source_vector, list) or len(source_vector) != 384:
        raise RuntimeError("source vectors were not generated by MiniLM")

    # A write only after all imports pass prevents a failed seed from looking
    # like a trustworthy pre-agent baseline.
    _BASELINE_PATH.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "objects": objects,
                "schema": _request(f"/v1/schema/{_COLLECTION}"),
            },
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    seed()
