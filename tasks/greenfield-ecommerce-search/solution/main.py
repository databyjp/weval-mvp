"""Ingest the supplied catalog and serve the Oracle's paginated search API."""

# pyright: reportMissingImports=false

import json
import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict, cast

import weaviate
from fastapi import FastAPI, Query
from search_backend import ProductCollection, ProductProperties, search_products
from weaviate import WeaviateClient
from weaviate.classes.config import Configure, DataType, Property, Tokenization
from weaviate.classes.data import DataObject
from weaviate.util import generate_uuid5


class SearchResponse(TypedDict):
    """Response body returned by the search endpoint."""

    items: list[ProductProperties]
    page: int
    page_size: int


def connect_to_weaviate() -> WeaviateClient:
    """Connect to the submission-owned Weaviate service.

    Reads ``WEAVIATE_HTTP_HOST``, ``WEAVIATE_HTTP_PORT``,
    ``WEAVIATE_GRPC_HOST``, and ``WEAVIATE_GRPC_PORT`` from the Task environment.
    Configuration and connection failures are retried for 60 attempts with a
    one-second pause after each failure.

    Returns:
        A connected client that the caller must close.

    Raises:
        RuntimeError: Weaviate does not become ready within the retry period.
    """
    last_error = None
    for _ in range(60):
        try:
            return weaviate.connect_to_custom(
                http_host=os.environ["WEAVIATE_HTTP_HOST"],
                http_port=int(os.environ["WEAVIATE_HTTP_PORT"]),
                http_secure=False,
                grpc_host=os.environ["WEAVIATE_GRPC_HOST"],
                grpc_port=int(os.environ["WEAVIATE_GRPC_PORT"]),
                grpc_secure=False,
            )
        except Exception as error:  # noqa: BLE001
            last_error = error
            time.sleep(1)
    raise RuntimeError("Weaviate did not become ready") from last_error


def prepare_collection(client: WeaviateClient) -> ProductCollection:
    """Create Product in an empty Trial environment and ingest the catalog.

    The Product schema uses the local vectorizer and field tokenization for SKU.
    Products come from ``/fixtures/products.json`` and receive deterministic
    UUIDs derived from their SKUs. A pre-existing Product collection is an error
    rather than reusable state. Exceptions raised by the Weaviate client during
    schema creation or insertion propagate unchanged.

    Returns:
        The collection handle backed by ``client`` after catalog insertion.

    Raises:
        RuntimeError: The supplied catalog cannot be read or decoded.
    """
    # A pre-existing collection means state leaked into this Trial. Let creation
    # fail so the evaluator preserves that evidence instead of hiding the defect.
    client.collections.create(
        name="Product",
        vector_config=Configure.Vectors.text2vec_transformers(),
        properties=[
            Property(
                name="sku",
                data_type=DataType.TEXT,
                tokenization=Tokenization.FIELD,
            ),
            Property(name="name", data_type=DataType.TEXT),
            Property(name="description", data_type=DataType.TEXT),
            Property(
                name="category",
                data_type=DataType.TEXT,
                tokenization=Tokenization.FIELD,
            ),
            Property(name="price", data_type=DataType.NUMBER),
        ],
    )
    collection = client.collections.use(
        "Product",
        data_model_properties=ProductProperties,
    )
    try:
        products = cast(
            list[ProductProperties],
            json.loads(Path("/fixtures/products.json").read_text()),
        )
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Could not load the supplied product catalog") from error
    catalog_objects = [
        DataObject(
            properties=product,
            uuid=generate_uuid5(product["sku"]),
        )
        for product in products
    ]
    collection.data.insert_many(catalog_objects)
    return collection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Own the Weaviate client and prepared Product collection.

    Closes the client when collection preparation fails or the application
    exits.
    """
    client = connect_to_weaviate()
    try:
        app.state.weaviate = client
        app.state.products = prepare_collection(client)
        yield
    finally:
        client.close()


app = FastAPI(lifespan=lifespan)


@app.get("/search")
def search(
    query: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1),
) -> SearchResponse:
    """Return one page from the prepared Product collection.

    FastAPI requires ``query`` and rejects page or page size values below one.
    The one-based page number is translated to a Weaviate result offset.
    """
    collection: ProductCollection = app.state.products
    items = search_products(
        collection,
        query=query,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
    }
