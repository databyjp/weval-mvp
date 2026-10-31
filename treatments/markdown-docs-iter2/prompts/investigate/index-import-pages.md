We're building product search with Weaviate over about 5 million product descriptions, embedded through Weaviate's `text2vec-openai` module with OpenAI's `text-embedding-3-small` (1,536 dimensions). Search must handle high query throughput at low latency, and we want to reduce the vector index's memory use without losing much recall. We'll import the catalog from a JSONL file with one product per line (`title` and `description`), and we'll use Python, TypeScript, and Go.

Read these pages of the Weaviate docs, and the code example pages they link to, and no others:

- https://feat-markdown-export-iter2--docs-weaviate-io.netlify.app/weaviate/concepts/vector-index.md
- https://feat-markdown-export-iter2--docs-weaviate-io.netlify.app/weaviate/concepts/vector-quantization.md
- https://feat-markdown-export-iter2--docs-weaviate-io.netlify.app/weaviate/concepts/data-import.md
- https://feat-markdown-export-iter2--docs-weaviate-io.netlify.app/weaviate/configuration/compression/rq-compression.md
- https://feat-markdown-export-iter2--docs-weaviate-io.netlify.app/weaviate/manage-objects/import.md

Use only these pages and their code example pages: don't fetch other URLs, install packages, or run code to check your answer.

From them, recommend the vector index, compression, and import method for this project, and write the code in each language. Write your findings to `/app/findings.json` in the format described in `WORKSPACE.md`, citing the page each answer came from.
