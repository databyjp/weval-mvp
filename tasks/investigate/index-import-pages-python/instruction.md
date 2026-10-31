We're building product search with Weaviate over about 5 million product descriptions, embedded through Weaviate's `text2vec-openai` module with OpenAI's `text-embedding-3-small` (1,536 dimensions). Search must handle high query throughput at low latency, and we want to reduce the vector index's memory use without losing much recall. We'll import the catalog from a JSONL file with one product per line (`title` and `description`), and we'll use Python.

Read these pages of the Weaviate docs, and no others:

- https://docs.weaviate.io/weaviate/concepts/vector-index
- https://docs.weaviate.io/weaviate/concepts/vector-quantization
- https://docs.weaviate.io/weaviate/concepts/data-import
- https://docs.weaviate.io/weaviate/configuration/compression/rq-compression
- https://docs.weaviate.io/weaviate/manage-objects/import

Use only these pages: don't fetch other URLs, install packages, or run code to check your answer.

From them, recommend the vector index, compression, and import method for this project, and write the Python code. Write your findings to `/app/findings.json` in the format described in `WORKSPACE.md`, citing the page each answer came from.
