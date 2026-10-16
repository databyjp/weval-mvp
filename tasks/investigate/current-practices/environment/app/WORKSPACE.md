# Weaviate research workspace

Write `/app/findings.json` as one JSON object with these keys:

- `weaviate_version`: the latest Weaviate server release.
- `python_client_version`: the latest Weaviate Python client release.
- `deployment`: how to deploy Weaviate.
- `vectorization`: how to vectorize data.
- `indexing`: which indexing settings to use.
- `search`: how to search.

Each value is an object with two keys:

- `answer`: your finding, as a string.
- `sources`: a list of the URLs the answer came from.

For example:

```json
{
  "deployment": {
    "answer": "...",
    "sources": ["https://..."]
  }
}
```
