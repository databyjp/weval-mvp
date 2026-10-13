"""Search the existing DocumentChunk collection with the Python Weaviate client.

GET /search?query=...&limit=... returns {"items": [...]}, where each item has
``document_id``, ``chunk_index``, ``title``, and ``text``. A nonempty query is
required; limit defaults to five and accepts integers from one through 25.
"""

import os
from typing import Any

import weaviate
from fastapi import FastAPI, Query

_COLLECTION = "DocumentChunk"
app = FastAPI(title="Document search")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the application process can receive requests."""
    return {"status": "ok"}


@app.get("/search")
def search(
    query: str = Query(min_length=1),
    limit: int = Query(default=5, ge=1, le=25),
) -> dict[str, list[dict[str, Any]]]:
    """Return live near-text matches from the evaluator-prepared collection.

    Each request opens and closes a Weaviate client using the Task environment's
    HTTP and gRPC endpoints.
    """
    with weaviate.connect_to_custom(
        http_host=os.environ["WEAVIATE_HTTP_HOST"],
        http_port=int(os.environ["WEAVIATE_HTTP_PORT"]),
        http_secure=False,
        grpc_host=os.environ["WEAVIATE_GRPC_HOST"],
        grpc_port=int(os.environ["WEAVIATE_GRPC_PORT"]),
        grpc_secure=False,
    ) as client:
        matches = client.collections.use(_COLLECTION).query.near_text(
            query=query, limit=limit
        )
        return {
            "items": [
                {
                    "document_id": obj.properties["document_id"],
                    "chunk_index": obj.properties["chunk_index"],
                    "title": obj.properties["title"],
                    "text": obj.properties["text"],
                }
                for obj in matches.objects
            ]
        }
