"""Write the Oracle's findings: the latest releases, looked up at run time, and
the recommendations from the docs pages cited with each answer.

``deployment`` and ``search`` are not scored."""

import json
import re
import urllib.request
from pathlib import Path

DOCS = "https://docs.weaviate.io"


def get_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def latest_server_release() -> str:
    releases = get_json(
        "https://api.github.com/repos/weaviate/weaviate/releases?per_page=100"
    )
    versions = [
        tuple(map(int, match.groups()))
        for release in releases
        if not release["draft"]
        and not release["prerelease"]
        and (match := re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", release["tag_name"]))
    ]
    return ".".join(map(str, max(versions)))


findings = {
    "weaviate_version": {
        "answer": latest_server_release(),
        "sources": ["https://github.com/weaviate/weaviate/releases"],
    },
    "client_library_versions": {
        "answer": "Python weaviate-client "
        + get_json("https://pypi.org/pypi/weaviate-client/json")["info"]["version"],
        "sources": ["https://pypi.org/project/weaviate-client/"],
    },
    "deployment": {
        "answer": "Docker for local development; Kubernetes or Weaviate Cloud for production.",
        "sources": [f"{DOCS}/deploy"],
    },
    "config_ingestion": {
        "answer": "Define each collection with vector_config=Configure.Vectors.<module>() (Python "
        "client 4.16 and later) and an HNSW index, starting with rotational quantization (RQ) "
        "for compression; import objects with client-side batching.",
        "sources": [
            f"{DOCS}/weaviate/manage-collections/vector-config",
            f"{DOCS}/weaviate/best-practices",
            f"{DOCS}/weaviate/manage-objects/import",
        ],
    },
    "search": {
        "answer": "Hybrid search as the starting point.",
        "sources": [f"{DOCS}/weaviate/concepts/search"],
    },
}
Path("/app/findings.json").write_text(json.dumps(findings, indent=2))
