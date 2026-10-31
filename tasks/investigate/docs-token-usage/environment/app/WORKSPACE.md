# Weaviate research workspace

Write `/app/findings.json` as one JSON object with these keys:

- `weaviate_version`: the latest Weaviate server release.
- `client_library_versions`: the corresponding Weaviate client versions.
- `deployment`: how to deploy Weaviate.
- `config_ingestion`: how to configure the DB & ingest data
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
