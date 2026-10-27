---
name: weaviate-best-practices
description: Current Weaviate practice for a new project, including which server and client versions to use and where to confirm the latest release, collection and vectorizer configuration, property tokenization, and search. Use before choosing a Weaviate version or writing Weaviate configuration or client code.
---

# Weaviate best practices

Weaviate's APIs changed in recent releases, and examples from memory or older
blog posts often use the legacy forms. Check versions and APIs against the
sources below before writing configuration.

## Versions

- Run the latest stable server release. Look it up: the GitHub releases page
  (https://github.com/weaviate/weaviate/releases) or the Docker image tags
  for `cr.weaviate.io/semitechnologies/weaviate`. Pin the full
  `major.minor.patch` tag, not `latest`.
- Use the latest Python client, `weaviate-client` on PyPI
  (https://pypi.org/pypi/weaviate-client/json). The docs release-notes table
  lists client versions by minor line (`4.24.x`); PyPI has the patch.
- If a project already pins a client version, keep the server within the
  range that client supports, and write code for the pinned client.
- Python client v3 (`weaviate.Client(...)`) is deprecated. Use v4:
  `weaviate.connect_to_local()`, `weaviate.connect_to_custom()`, or
  `weaviate.connect_to_weaviate_cloud()`, and close the client when done.

## Collections and vectors

- Define collections explicitly rather than relying on auto-schema.
- Since Python client 4.16.0, vectorizers are configured with
  `vector_config=Configure.Vectors.<module>(...)`. Each entry is a named
  vector, which can take `name=` and `source_properties=`. The legacy forms,
  `vectorizer_config=Configure.Vectorizer...` and `Configure.NamedVectors`,
  are deprecated. Use `Configure.Vectors.self_provided()` when the
  application supplies its own vectors.
- A vectorizer module must be enabled on the server (`ENABLE_MODULES`) and,
  for local models, its inference service must run beside Weaviate:
  `text2vec-transformers` with `TRANSFORMERS_INFERENCE_API`, or
  `text2vec-ollama` with an Ollama endpoint. Weaviate applies no default
  vectorizer.
- `collection.config.add_vector()` adds a named vector to an existing
  collection, but an existing vector's vectorizer and a property's
  tokenization can't be changed. Plan them before the first import, or
  recreate the collection.

```python
from weaviate.classes.config import Configure, DataType, Property

client.collections.create(
    "Article",
    vector_config=Configure.Vectors.text2vec_transformers(
        name="body", source_properties=["title", "body"],
    ),
    properties=[
        Property(name="title", data_type=DataType.TEXT),
        Property(name="body", data_type=DataType.TEXT),
    ],
)
```

## Properties and tokenization

- `text` properties default to `word` tokenization, which splits on
  non-alphanumeric characters and lowercases. Identifiers that must match
  exactly, such as codes, slugs, or email addresses, need `field`
  tokenization (`tokenization=Tokenization.FIELD`), and usually
  `skip_vectorization=True`.
- Use `int`, `number`, `boolean`, and `date` types for values you filter or
  sort on, rather than strings.
- Set `index_filterable` or `index_range_filters` for properties you filter
  on; set `index_searchable=False` for text never used in keyword search.

## Import

- Import with a batch context: `collection.batch.dynamic()` or
  `collection.batch.fixed_size(batch_size=...)`. After the context exits,
  read `collection.batch.failed_objects`; batch errors do not raise.
- Give objects deterministic UUIDs (`weaviate.util.generate_uuid5(key)`) so
  re-running an import updates objects instead of duplicating them.

## Search

- `collection.query.hybrid(query, alpha=...)` combines BM25 and vector
  search; `alpha=0` is keyword only and `alpha=1` is vector only. Set
  `alpha` explicitly; the default depends on the client.
- `query.bm25` is keyword only. `query.near_text` needs a vectorizer;
  `query.near_vector` takes your own vector.
- Filter with `filters=Filter.by_property("x").equal(...)`; use
  `Filter.by_id()` for UUIDs.
- Page with `limit` and `offset` for user-facing results. To read a whole
  collection, iterate with `collection.iterator()`, which uses a cursor.
  `QUERY_MAXIMUM_RESULTS` caps `offset + limit`.

## Operations

- Multi-tenancy (`Configure.multi_tenancy(enabled=True)`) isolates tenants'
  data in one collection; enable it at creation.
- Vector compression (`quantizer=Configure.VectorIndex.Quantizer.rq()` on a
  `Configure.Vectors` entry, or `pq`, `bq`, `sq`) reduces memory use for
  large collections.
- Back up with a backup module (`backup-filesystem`, `backup-s3`, ...).
  Upgrade one minor version at a time.
- Enable API-key or OIDC authentication for anything beyond local use.
