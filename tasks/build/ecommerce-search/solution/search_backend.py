"""Canonical Weaviate hybrid-search implementation for the Oracle."""

# pyright: reportMissingImports=false

from typing import TypedDict

from weaviate.collections import Collection


class ProductProperties(TypedDict):
    """Product fields stored in Weaviate and returned by the search endpoint."""

    sku: str
    name: str
    description: str
    category: str
    price: float


type ProductCollection = Collection[ProductProperties, None]


def search_products(
    collection: ProductCollection,
    *,
    query: str,
    limit: int,
    offset: int,
) -> list[ProductProperties]:
    """Return one ordered page from Weaviate hybrid search.

    ``query``, ``limit``, and ``offset`` pass unchanged to Weaviate. Returned
    properties preserve the result order selected by Weaviate.
    """
    result = collection.query.hybrid(
        query=query,
        limit=limit,
        offset=offset,
    )
    return [item.properties for item in result.objects]
