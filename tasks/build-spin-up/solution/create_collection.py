"""Create the Oracle's DocumentChunk collection with a text2vec-transformers named vector."""

import os

import weaviate
from weaviate.classes.config import Configure, DataType, Property

with weaviate.connect_to_custom(
    http_host=os.environ["WEAVIATE_HTTP_HOST"],
    http_port=int(os.environ["WEAVIATE_HTTP_PORT"]),
    http_secure=False,
    grpc_host=os.environ["WEAVIATE_GRPC_HOST"],
    grpc_port=int(os.environ["WEAVIATE_GRPC_PORT"]),
    grpc_secure=False,
) as client:
    client.collections.create(
        "DocumentChunk",
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.text2vec_transformers(name="text"),
    )
