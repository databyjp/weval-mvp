---
motivation: >
  How many tokens does an agent spend reading a fixed set of Weaviate docs
  pages to recommend an index, compression, and import method and write the
  code for them, and does serving those pages as Markdown reduce that?
---

# investigate/index-import-pages

The prompt names the five pages to read, three concepts pages and two how-to
pages, so the agent's navigation is fixed. In
[`investigate/docs-token-usage`](docs-token-usage.md) and
[`investigate/client-code-examples`](client-code-examples.md), which pages an
agent opens, and how many, varies more between Trials than a change to the
page format does (`plan/docs-improvements.md`, iteration 1). Fixing the pages
leaves the page format and the agent's tools as the main sources of token
variation.

The concepts pages carry the recommendations; the how-to pages carry the
syntax, with the TypeScript and Go code in tabs that the HTML hides. The
[`markdown-docs-staging`](../../../treatments/markdown-docs-staging/README.md)
and [`markdown-docs-iter1`](../../../treatments/markdown-docs-iter1/README.md)
Treatments replace the prompt with the same pages' Markdown versions on their
staging builds.

## Boundary conditions

### Prompt

> We're building product search with Weaviate over about 5 million product
> descriptions, embedded through Weaviate's `text2vec-openai` module with
> OpenAI's `text-embedding-3-small` (1,536 dimensions). Search must handle
> high query throughput at low latency, and we want to reduce the vector
> index's memory use without losing much recall. We'll import the catalog
> from a JSONL file with one product per line (`title` and `description`),
> and we'll use Python, TypeScript, and Go.
>
> Read these pages of the Weaviate docs, and no others:
>
> - https://docs.weaviate.io/weaviate/concepts/vector-index
> - https://docs.weaviate.io/weaviate/concepts/vector-quantization
> - https://docs.weaviate.io/weaviate/concepts/data-import
> - https://docs.weaviate.io/weaviate/configuration/compression/rq-compression
> - https://docs.weaviate.io/weaviate/manage-objects/import
>
> From them, recommend the vector index, compression, and import method for
> this project, and write the code in each language. Write your findings to
> `/app/findings.json` in the format described in `WORKSPACE.md`, citing the
> page each answer came from.

### Workspace

- `WORKSPACE.md`: the `findings.json` format. It has three items
  (`vector_index`, `compression`, `batch_import`), each with an `answer`
  string and a `sources` list of URLs. `vector_index` and `batch_import` also
  have a `code` object with `python`, `typescript`, and `go` strings: the
  collection creation and the JSONL import.

### Initial state

Nothing is running.

## Observations

`snapshot.py` records the submitted `findings.json`. The code is not run.
`weval.json`'s `usage.urls` shows whether the agent kept to the five pages.

## Checks

Neither the recommendations nor the code are scored: the Task measures the
tokens spent reading the pages. Compare answers against the Oracle's below.

| Check | Tier | Validation |
|---|---|---|
| `findings-file` | REQUIRED | `/app/findings.json` is a JSON object with every documented item, each with an `answer` string and a `sources` list, and `python`, `typescript`, and `go` code strings for `vector_index` and `batch_import`. |

## Calibration

Variants are in `tests/test_investigate_index_import_pages_check.py`. The
Oracle adapts the how-to pages' Python, TypeScript, and Go (v6) examples to
the scenario, with these answers:

| Item | Oracle answer | Source |
|---|---|---|
| `vector_index` | HNSW with default settings (dynamic `ef`): the concepts page recommends it for large collections with high query throughput and low latency. | `concepts/vector-index` |
| `compression` | 8-bit RQ: recommended for most use cases, about 4x compression at 98-99% recall, no training step. | `concepts/vector-quantization`, `configuration/compression/rq-compression` |
| `batch_import` | Server-side batching: `data.ingest()` in Python and TypeScript, `collection.Batch(ctx, ...)` in Go v6. | `concepts/data-import`, `manage-objects/import` |

The pages disagree on Go. `concepts/data-import` says "The Go client does not
yet support them; use client-side batching instead", while
`manage-objects/import` shows server-side batching in its Go (v6) tab and says
only the Go v5 client lacks it. An answer that uses manual batching in Go
followed the concepts page.

| Variant | Fails | Models |
|---|---|---|
| `missing_file` | every check | No `findings.json` was written. |
| `missing_item` | `findings-file` | `compression` is absent. |
| `missing_language` | `findings-file` | `batch_import` has no Go code. |
