Source: https://docs.weaviate.io/weaviate/client-libraries/python

# Python

Python client (SDK)

The latest Python client is version `v4.24.1`.

[weaviate/weaviate-python-client](https://github.com/weaviate/weaviate-python-client)[Reference manual (docstrings)](https://weaviate-python-client.readthedocs.io/en/latest/)

This page broadly covers the Weaviate Python client (`v4` release). For usage information not specific to the Python client, such as code examples, see the relevant pages in the [How-to manuals & Guides](/weaviate/guides).

## Installation

The Python client library requires Python 3.10 or later. It is available on [PyPI.org](https://pypi.org/project/weaviate-client/), and can be installed with:

```bash
pip install -U weaviate-client
```

For installing beta versions

```bash
pip install --pre -U "weaviate-client==4.*"`
```

Requirements: Weaviate version compatibility & gRPC

#### Weaviate version compatibility

The `v4` Python client requires Weaviate `v1.27.0` and later. Against an older server the client raises `Weaviate version <version> is not supported. Please use Weaviate version 1.27.0 or higher.` Generally, we encourage you to use the latest version of the Python client and the Weaviate Database.

In Weaviate Cloud, clusters are compatible with the `v4` client as of 31 January, 2024. Clusters created before this date will not be compatible with the `v4` client.

#### gRPC

The `v4` client uses remote procedure calls (RPCs) under-the-hood. Accordingly, a port for gRPC must be open to your Weaviate server.

docker-compose.yml example

If you are running Weaviate with Docker, you can map the default port (`50051`) by adding the following to your `docker-compose.yml` file:

```yaml
ports:
  - 8080:8080
  - 50051:50051
```

#### Query Agent

You can install the Weaviate client library with the optional `agents` extras to use the [Query Agent](/query-agent). Install the client library using the following command:

```bash
pip install -U "weaviate-client[agents]"
```

## Get started

Prerequisites

If you haven't yet, we recommend going through the [**Quickstart tutorial**](/weaviate/quickstart) first to get the most out of this section.

Get started with Weaviate using this Python example. The code walks you through these key steps:

1. **[Connect to Weaviate](/weaviate/connections)**: Establish a connection to a local (or Cloud) Weaviate instance.
2. **[Create a collection](/weaviate/manage-collections)**: Define the data schema for a `Question` collection, using an Ollama model to vectorize the data.
3. **[Import data](/weaviate/manage-objects/import)**: Fetch sample Jeopardy questions and use Weaviate's batch import for efficient ingestion and automatic vector embedding generation.
4. **[Search/query the database](/weaviate/search)**: Execute a vector search to find questions semantically similar to the query `biology`.

.Vectors.text2vec\_xxx with AutoSchema

Defining a collection with `Configure.Vectors.text2vec_xxx()` with Python client library `4.16.0`-`4.16.3` will throw an error if no properties are defined and `vectorize_collection_name` is not set to `True`.

This is addressed in `4.16.4` of the Weaviate Python client. See this FAQ entry for more details: [Invalid properties error in Python client versions 4.16.0 to 4.16.3](/weaviate/more-resources/faq#q-invalid-properties-error-when-creating-a-collection-python-client-versions-4160-to-4163).

```py
import weaviate
import requests, json
from weaviate.classes.config import Configure

client = weaviate.connect_to_local()

questions = client.collections.create(
    name="Question",
    vector_config=Configure.Vectors.text2vec_ollama(
        api_endpoint="http://ollama:11434",  # If using Docker you might need: http://host.docker.internal:11434
        model="nomic-embed-text",  # The model to use
    ),  # Configure the Ollama embedding model
)

resp = requests.get(
    "https://raw.githubusercontent.com/weaviate-tutorials/quickstart/main/data/jeopardy_tiny.json"
)
data = json.loads(resp.text)

with questions.batch.dynamic() as batch:
    for d in data:
        batch.add_object(
            {
                "answer": d["Answer"],
                "question": d["Question"],
                "category": d["Category"],
            }
        )
        if batch.number_errors > 10:
            print("Batch import stopped due to excessive errors.")
            break

failed_objects = questions.batch.failed_objects
if failed_objects:
    print(f"Number of failed imports: {len(failed_objects)}")
    print(f"First failed object: {failed_objects[0]}")

response = questions.query.near_text(query="biology", limit=2)

for obj in response.objects:
    print(json.dumps(obj.properties, indent=2))

client.close()  # Free up resources
```

For more code examples, check out the [How-to manuals & Guides](/weaviate/guides) section.

## Asynchronous usage

The Python client library provides a synchronous API by default through the `WeaviateClient` class, which is covered on this page. An asynchronous API is also available through the `WeaviateAsyncClient` class (from `weaviate-client` `v4.7.0` and up). See the [async client API page](/weaviate/client-libraries/python/async) for further details.

## Releases

Go to the [GitHub releases page](https://github.com/weaviate/weaviate-python-client/releases) to see the history of the Python client library releases and change logs.

Click here for a table of Weaviate and corresponding client versions

This table lists recent Weaviate Database versions and corresponding client library versions.

| Weaviate Database  ([GitHub](https://github.com/weaviate/weaviate/releases)) | First  release date | Python  ([GitHub](https://github.com/weaviate/weaviate-python-client/releases)) | TypeScript/  JavaScript  ([GitHub](https://github.com/weaviate/typescript-client/releases)) | Go  ([GitHub](https://github.com/weaviate/weaviate-go-client/releases)) | Java  ([GitHub](https://github.com/weaviate/java-client/releases)) | C#  ([GitHub](https://github.com/weaviate/csharp-client/releases)) |
| --- | --- | --- | --- | --- | --- | --- |
| [1.40.x](https://github.com/weaviate/weaviate/releases/tag/v1.40.0) | 2026-10-07 | [4.24.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.24.0) | [3.15.x](https://github.com/weaviate/typescript-client/releases/tag/v3.15.1) | [6.0.0](https://github.com/weaviate/weaviate-go-client/releases/tag/v6.0.0) | [6.3.2](https://github.com/weaviate/java-client/releases/tag/6.3.2) | - |
| [1.39.x](https://github.com/weaviate/weaviate/releases/tag/v1.39.0) | 2026-08-04 | [4.23.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.23.0) | [3.15.x](https://github.com/weaviate/typescript-client/releases/tag/v3.15.0) | - | [6.3.1](https://github.com/weaviate/java-client/releases/tag/6.3.1) | [1.2.0](https://github.com/weaviate/csharp-client/releases/tag/1.2.0) |
| [1.38.x](https://github.com/weaviate/weaviate/releases/tag/v1.38.0) | 2026-06-05 | [4.22.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.22.0) | [3.14.x](https://github.com/weaviate/typescript-client/releases/tag/v3.14.0) | - | [6.3.0](https://github.com/weaviate/java-client/releases/tag/6.3.0) | [1.2.0](https://github.com/weaviate/csharp-client/releases/tag/1.2.0) |
| [1.37.x](https://github.com/weaviate/weaviate/releases/tag/v1.37.0) | 2026-04-16 | [4.21.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.21.0) | [3.13.x](https://github.com/weaviate/typescript-client/releases/tag/v3.13.0) | [5.7.3](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.7.3) | [6.2.0](https://github.com/weaviate/java-client/releases/tag/6.2.0) | [1.1.1](https://github.com/weaviate/csharp-client/releases/tag/1.1.1) |
| [1.36.x](https://github.com/weaviate/weaviate/releases/tag/v1.36.0) | 2026-02-24 | [4.20.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.20.0) | [3.12.x](https://github.com/weaviate/typescript-client/releases/tag/v3.12.0) | [5.7.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.7.0) | [6.1.0](https://github.com/weaviate/java-client/releases/tag/6.1.0) | [1.0.1](https://github.com/weaviate/csharp-client/releases/tag/1.0.1) |

Older releases

| Weaviate Database  ([GitHub](https://github.com/weaviate/weaviate/releases)) | First  release date | Python  ([GitHub](https://github.com/weaviate/weaviate-python-client/releases)) | TypeScript/  JavaScript  ([GitHub](https://github.com/weaviate/typescript-client/releases)) | Go  ([GitHub](https://github.com/weaviate/weaviate-go-client/releases)) | Java  ([GitHub](https://github.com/weaviate/java-client/releases)) | C#  ([GitHub](https://github.com/weaviate/csharp-client/releases)) |
| --- | --- | --- | --- | --- | --- | --- |
| [1.35.x](https://github.com/weaviate/weaviate/releases/tag/v1.35.0) | 2025-12-17 | [4.19.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.19.0) | [3.11.x](https://github.com/weaviate/typescript-client/releases/tag/v3.11.0) | [5.6.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.6.0) | [6.0.0](https://github.com/weaviate/java-client/releases/tag/6.0.0) | [1.0.0](https://github.com/weaviate/csharp-client/releases/tag/1.0.0) |
| [1.34.x](https://github.com/weaviate/weaviate/releases/tag/v1.34.0) | 2025-11-05 | [4.18.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.18.0) | [3.10.x](https://github.com/weaviate/typescript-client/releases/tag/v3.10.0) | [5.6.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.6.0) | [6.0.0](https://github.com/weaviate/java-client/releases/tag/6.0.0) | - |
| [1.33.x](https://github.com/weaviate/weaviate/releases/tag/v1.33.0) | 2025-09-25 | [4.17.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.17.0) | [3.9.x](https://github.com/weaviate/typescript-client/releases/tag/v3.9.0) | [5.5.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.5.0) | [5.5.x](https://github.com/weaviate/java-client/releases/tag/5.5.0) | - |
| [1.32.x](https://github.com/weaviate/weaviate/releases/tag/v1.32.0) | 2025-07-14 | [4.16.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.16.0) | [3.8.x](https://github.com/weaviate/typescript-client/releases/tag/v3.8.0) | [5.3.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.3.0) | [5.4.x](https://github.com/weaviate/java-client/releases/tag/5.4.0) | - |
| [1.31.x](https://github.com/weaviate/weaviate/releases/tag/v1.31.0) | 2025-05-30 | [4.15.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.15.0) | [3.6.x](https://github.com/weaviate/typescript-client/releases/tag/v3.6.0) | [5.2.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.2.0) | [5.3.x](https://github.com/weaviate/java-client/releases/tag/5.3.0) | - |
| [1.30.x](https://github.com/weaviate/weaviate/releases/tag/v1.30.0) | 2025-04-03 | [4.12.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.12.0) | [3.5.x](https://github.com/weaviate/typescript-client/releases/tag/v3.5.0) | [5.1.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.1.0) | [5.2.x](https://github.com/weaviate/java-client/releases/tag/5.2.0) | - |
| [1.29.x](https://github.com/weaviate/weaviate/releases/tag/v1.29.0) | 2025-02-17 | [4.11.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.11.0) | [3.4.x](https://github.com/weaviate/typescript-client/releases/tag/v3.4.0) | [5.0.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v5.0.0) | [5.1.x](https://github.com/weaviate/java-client/releases/tag/5.1.0) | - |
| [1.28.x](https://github.com/weaviate/weaviate/releases/tag/v1.28.0) | 2024-12-11 | [4.10.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.10.0) | [3.3.x](https://github.com/weaviate/typescript-client/releases/tag/v3.3.0) | [4.16.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v4.16.0) | [5.0.x](https://github.com/weaviate/java-client/releases/tag/5.0.0) | - |
| [1.27.x](https://github.com/weaviate/weaviate/releases/tag/v1.27.0) | 2024-10-16 | [4.9.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.9.0) | [3.2.x](https://github.com/weaviate/typescript-client/releases/tag/v3.2.0) | [4.16.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v4.16.0) | [5.0.x](https://github.com/weaviate/java-client/releases/tag/5.0.0) [4.9.x](https://github.com/weaviate/java-client/releases/tag/4.9.0) | - |
| [1.26.x](https://github.com/weaviate/weaviate/releases/tag/v1.26.0) | 2024-07-22 | [4.7.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.7.0) | [3.1.x](https://github.com/weaviate/typescript-client/releases/tag/v3.1.0) | [4.15.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v4.15.0) | [4.8.x](https://github.com/weaviate/java-client/releases/tag/4.8.0) | - |
| [1.25.x](https://github.com/weaviate/weaviate/releases/tag/v1.25.0) | 2024-05-10 | [4.6.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.6.0) | [2.1.x](https://github.com/weaviate/typescript-client/releases/tag/v2.1.0) | [4.13.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v4.13.0) | [4.6.x](https://github.com/weaviate/java-client/releases/tag/4.6.0) | - |
| [1.24.x](https://github.com/weaviate/weaviate/releases/tag/v1.24.0) | 2024-02-27 | [4.5.x](https://github.com/weaviate/weaviate-python-client/releases/tag/v4.5.0) | [2.0.x](https://github.com/weaviate/typescript-client/releases/tag/v2.0.0) | [4.10.x](https://github.com/weaviate/weaviate-go-client/releases/tag/v4.10.0) | [4.4.x](https://github.com/weaviate/java-client/releases/tag/4.4.0) | - |
| 1.23.x | 2023-12-18 | 3.26.x | 1.5.x | 4.10.x | 4.4.x | - |
| 1.22.x | 2023-10-27 | 3.25.x | 1.5.x | 4.10.x | 4.3.x | - |
| 1.21.x | 2023-08-17 | 3.22.x | 1.4.x | 4.9.x | 4.2.x | - |
| 1.20.x | 2023-07-06 | 3.22.x | 1.1.x | 4.7.x | 4.2.x | - |
| 1.19.x | 2023-05-04 | 3.17.x | 1.1.x[1](#typescript-client-change) | 4.7.x | 4.0.x | - |
| 1.18.x | 2023-03-07 | 3.13.x | 2.14.x | 4.6.x | 3.6.x | - |
| 1.17.x | 2022-12-20 | 3.9.x | 2.14.x | 4.5.x | 3.5.x | - |
| 1.16.x | 2022-10-31 | 3.8.x | 2.13.x | 4.4.x | 3.4.x | - |
| 1.15.x | 2022-09-07 | 3.6.x | 2.12.x | 4.3.x | 3.3.x | - |
| 1.14.x | 2022-07-07 | 3.6.x | 2.11.x | 4.2.x | 3.2.x | - |
| 1.13.x | 2022-05-03 | 3.4.x | 2.9.x | 4.0.x | 2.4.x | - |
| 1.12.x | 2022-04-05 | 3.4.x | 2.8.x | 3.0.x | 2.3.x | - |
| 1.11.x | 2022-03-14 | 3.2.x | 2.7.x | 2.6.x | 2.3.x | - |
| 1.10.x | 2022-01-27 | 3.1.x | 2.5.x | 2.4.x | 2.1.x | - |
| 1.9.x | 2021-12-10 | 3.1.x | 2.4.x | 2.4.x | 2.1.x | - |
| 1.8.x | 2021-11-30 | 3.1.x | 2.4.x | 2.3.x | 1.1.x | - |
| 1.7.x | 2021-09-01 | 3.1.x | 2.4.x | 2.3.x | 1.1.x | - |
| 1.6.x | 2021-08-11 | 2.4.x | 2.3.x | 2.2.x | 1.0.x | - |
| 1.5.x | 2021-07-13 | 2.2.x | 2.1.x | 2.1.x | 1.0.x | - |
| 1.4.x | 2021-06-09 | 2.2.x | 2.1.x | 2.1.x | 1.0.x | - |
| 1.3.x | 2021-04-23 | 2.2.x | 2.1.x | 2.1.x | 1.0.x | - |
| 1.2.x | 2021-03-15 | 2.2.x | 2.0.x | 1.1.x | - | - |
| 1.1.x | 2021-02-10 | 2.1.x | - | - | - | - |
| 1.0.x | 2021-01-14 | 2.0.x | - | - | - | - |

#### TypeScript client change

The [TypeScript client](https://github.com/weaviate/typescript-client) replaced the [JavaScript client](https://github.com/weaviate/weaviate-javascript-client) on 2023-03-17.

#### Vectorizer API changes `v4.16.0`

.Vectors.text2vec\_xxx with AutoSchema

Defining a collection with `Configure.Vectors.text2vec_xxx()` with Python client library `4.16.0`-`4.16.3` will throw an error if no properties are defined and `vectorize_collection_name` is not set to `True`.

This is addressed in `4.16.4` of the Weaviate Python client. See this FAQ entry for more details: [Invalid properties error in Python client versions 4.16.0 to 4.16.3](/weaviate/more-resources/faq#q-invalid-properties-error-when-creating-a-collection-python-client-versions-4160-to-4163).

Starting with the Weaviate Python client `v4.16.0`, there are multiple changes to the vectorizer configuration API when creating collections:

* `.vectorizer_config` has been replaced with `.vector_config`
* `Configure.NamedVectors` has been replaced with `Configure.Vectors` and `Configure.MultiVectors`
* `Configure.NamedVectors.none` and `Configure.Vectorizer.none` have been replaced with `Configure.Vectors.self_provided` and `Configure.MultiVectors.self_provided`

#### Python client `v3` deprecation

The Weaviate Python client `v3` has been deprecated and should no longer be used. If you need documentation for the `v3` client, see the [documentation archive](https://archive.docs.weaviate.io/weaviate/client-libraries/python/python_v3). If you are migrating from the Python `v3` client to the `v4` client, see this [migration guide](https://archive.docs.weaviate.io/weaviate/client-libraries/python/v3_v4_migration).

#### Beta releases

Migration guides - beta releases

#### Changes in `v4.4b9`

##### `weaviate.connect_to_x` methods

The `timeout` argument in now a part of the `additional_config` argument. It takes the class `weaviate.config.AdditionalConfig` as input.

##### Queries

All optional arguments to methods in the `query` namespace now are enforced as keyword arguments.

There is now runtime logic for parsing query arguments enforcing the correct type.

##### Batch processing

Introduction of three distinct algorithms using different batching styles under-the-hood:

* `client.batch.dynamic()`
* `client.batch.fixed_size()`
* `client.batch.rate_limit()`

`client.batch.dynamic() as batch` is a drop-in replacement for the previous `client.batch as batch`, which is now deprecated and will be removed on release.

```python
with client.batch.dynamic() as batch:
  ...
```

is equivalent to:

```python
with client.batch as batch:
  ...
```

`client.batch.fixed_size() as batch` is a way to configure your batching algorithm to only use a fixed size.

```python
with client.batch.dynamic() as batch:
  ...
```

is equivalent to:

```python
client.batch.configure_fixed_size()
with client.batch as batch:
  ...
```

`client.batch.rate_limit() as batch` is a new way to help avoid hitting third-party vectorization API rate limits. By specifying `request_per_minute` in the
`rate_limit()` method, you can force the batching algorithm to send objects to Weaviate at the speed your third-party API is capable of processing objects.

These methods now return completely localized context managers. This means that `failed_objects` and `failed_references` of one batch won't be included
in any subsequent calls.

Finally, if the background thread responsible for sending the batches raises an exception this is now re-raised in the main thread rather than silently erroring.

##### Filters

The argument `prop` in `Filter.by_property` has been renamed to `name`

Ref counting is now achievable using `Filter.by_ref_count(ref)` rather than `Filter([ref])`

#### Changes in `v4.4b8`

##### Reference filters

Reference filters have a simplified syntax. The new syntax looks like this:

```python
Filter.by_ref("ref").by_property("target_property")
```

#### Changes in `v4.4b7`

##### Library imports

Importing directly from `weaviate` is deprecated. Use `import weaviate.classes as wvc` instead.

##### Close client connections

Starting in v4.4b7, you have to explicitly close your client connections. There are two ways to close client connections.

Use `client.close()` to explicitly close your client connections.

```python
import weaviate
client = weaviate.connect_to_local()

print(client.is_ready())

client.close()
```

Use a context manager to close client connections for you.

```python
import weaviate

with weaviate.connect_to_local() as client:
     print(client.is_ready())

# Python closes the client when you leave the 'with' block
```

##### Batch processing

The v4.4b7 client introduces changes to `client.batch`.

* `client.batch` requires a context manager.
* Manual mode is removed, you cannot send batches with `.create_objects`.
* Batch size and the number of concurrent requests are dynamically assigned. Use `batch.configure_fixed_size` to specify values.
* The `add_reference` method is updated.
* The `to_object_collection` method is removed.

Updated `client.batch` parameters

| Old value | Value in v4.4b7 |
| --- | --- |
| from\_object\_uuid: UUID | from\_uuid: UUID |
| from\_object\_collection: str | from\_collection: str |
| from\_property\_name: str | from\_property: str |
| to\_object\_uuid: UUID | to: Union[WeaviateReference, List[UUID]] |
| to\_object\_collection: Optional[str] = None |  |
| tenant: Optional[str] = None | tenant: Optional[str] = None |

##### Filter syntax

Filter syntax is updated in v4.4b7.

**NOTE**: The [filter reference syntax](#reference-filters) is simplified in 4.4b8.

| Old syntax | New syntax in v4.4b7 |
| --- | --- |
| Filter(path=property) | Filter.by\_property(property) |
| Filter(path=["ref", "target\_class", "target\_property"]) | Filter.by\_ref().link\_on("ref").by\_property("target\_property") |
| FilterMetadata.ByXX | Filter.by\_id()  Filter.by\_creation\_time()   Filter.by\_update\_time() |

The pre-4.4b7 filter syntax is deprecated. The new, v4.4b7 syntax looks like this.

```python
import weaviate
import datetime
import weaviate.classes as wvc

client = weaviate.connect_to_local()

jeopardy = client.collections.use("JeopardyQuestion")
response = jeopardy.query.fetch_objects(
    filters=wvc.query.Filter.by_property("round").equal("Double Jeopardy!") &
            wvc.query.Filter.by_creation_time().greater_or_equal(datetime.datetime(2005, 1, 1)) |
            wvc.query.Filter.by_creation_time().greater_or_equal(datetime.datetime(2000, 12, 31)),
            limit=3
    )

client.close()
```

##### `reference_add_many` updated

The `reference_add_many` syntax is updated; `DataReferenceOneToMany` is now `DataReference`.

```python
collection.data.reference_add_many(
    [
        DataReference(
            from_property="ref",
            from_uuid=uuid_from,
            to_uuid=*one or a list of UUIDs*,
        )
    ]
)
```

##### References

Multi-target references updated. These are the new functions:

* `ReferenceProperty.MultiTarget`
* `DataReference.MultiTarget`
* `QueryReference.MultiTarget`

Use `ReferenceToMulti` for multi-target references.

#### Older client changes

##### References

* References are now added through a `references` parameter during collection creation, object insertion and queries.
* The `FromReference` class is now called `QueryReference`.

##### Reorganization of classes/parameters

* `weaviate.classes` submodule further split into:
  + `weaviate.classes.config`
  + `weaviate.classes.data`
  + `weaviate.classes.query`
  + `weaviate.classes.generic`
* `vector_index_config` parameter factory functions for `wvc.config.Configure` and `wvc.config.Reconfigure` have changed to, e.g.:

  ```python
  client.collections.create(
      name="MyCollection",
      vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
          distance_metric=wvc.config.VectorDistances.COSINE,
          vector_cache_max_objects=1000000,
          quantizer=wvc.config.Configure.VectorIndex.Quantizer.pq()
      ),
  )
  ```

  + `vector_index_type` parameter has been removed.
* `vectorize_class_name` parameter in the `Property` constructor method is `vectorize_collection_name`.
* `[collection].data.update()` / `.replace()` \*args order changed, aiming to accommodate not providing properties when updating.
* `[collection].data.reference_add` / `.reference_delete` / `.reference_replace` the `ref` keyword was renamed to `to`.
* `collections.create()` / `get()`: `data_model` kwarg to keyword to provide generics was renamed to `data_model_properties` .
* `[object].metadata.uuid` is now `[object].uuid`.
* `[object].metadata.creation_time_unix` is now `[object].metadata.creation_time`.
* `[object].metadata.last_update_time_unix` is now `[object].metadata.last_update`.
* `quantitizer` is renamed to `quantizer`
* To request the vector in the returned data, use the `include_vector` parameter.

##### Data types

* Time metadata (for creation and last updated time) now returns a `datetime` object, and the parameters are renamed to `creation_time` and `last_update_time` under `MetadataQuery`.
  + `metadata.creation_time.timestamp() * 1000` will return the same value as before.
* `query.fetch_object_by_id()` now uses gRPC under the hood (rather than REST), and returns objects in the same format as other queries.
* `UUID` and `DATE` properties are returned as typed objects.

## Code examples & further resources

Usage information for various operations and features can be found throughout the Weaviate documentation.

[How-to: Configure Weaviate

Configure compression, backups, authentication, authorization, data replication and more.](/weaviate/configuration)[How-to: Manage collections

Manage collections (CRUD), configure vectorizers and index parameters, set up multi-tenancy, and perform migrations.](/weaviate/manage-collections)[How-to: Manage objects

Adding new objects, fetching existing ones, modifying them, and removing them from collections.](/weaviate/manage-objects)[How-to: Query & search

From basic vector and hybrid searches to specialized image queries and performing data aggregations.](/weaviate/search)

The Weaviate API reference pages for [search](/weaviate/api) and [REST](/weaviate/api/rest) may also be useful starting points.

![Weaviate Academy](/img/docs/weaviate-academy-purple.png)

#### Course: Your First AI App (Search and RAG)

A hands-on course where you will build a movie recommendation API with Weaviate and FastAPI.

[Open Academy Course](https://academy.weaviate.io/courses/wa180-py)

## Questions and feedback

Have a question or feedback? Here's how to reach us.

[Community Forum

Ask questions and connect with other developers on our Community forum.](https://forum.weaviate.io/c/support)[Support

Weaviate Cloud user or customer? Find the right channel on the Support page.](/support)
