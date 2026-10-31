# Weaviate research workspace

Write `/app/findings.json` as one JSON object with these keys:

- `deployment`: how to deploy Weaviate.
- `config_ingestion`: how to create a collection with a vectorizer and import data.
- `search`: how to search.

Each value is an object with these keys:

- `answer`: your finding, as a string.
- `sources`: a list of the URLs the answer came from.

`config_ingestion` and `search` also have:

- `code`: an object with `python`, `typescript`, and `go` keys, each holding
  that language's code as a string.

For example:

```json
{
  "search": {
    "answer": "...",
    "sources": ["https://..."],
    "code": {"python": "...", "typescript": "...", "go": "..."}
  }
}
```
