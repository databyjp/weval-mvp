# Weaviate research workspace

Write `/app/findings.json` as one JSON object with these keys:

- `vector_index`: the vector index type and settings to use.
- `compression`: the vector compression to use.
- `batch_import`: how to import the catalog.

Each value is an object with these keys:

- `answer`: your recommendation and the reason for it, as a string.
- `sources`: a list of the URLs the answer came from.

`vector_index` and `batch_import` also have:

- `code`: an object with a `python` key holding the Python code as a string.
  For `vector_index`, the code creates the collection with the index and
  compression you recommend; for `batch_import`, it imports the JSONL file
  into that collection.

For example:

```json
{
  "batch_import": {
    "answer": "...",
    "sources": ["https://..."],
    "code": {"python": "..."}
  }
}
```
