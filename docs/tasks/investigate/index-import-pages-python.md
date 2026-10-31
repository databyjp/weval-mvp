---
motivation: >
  For a reader who needs only Python, how many tokens does an agent spend
  reading a fixed set of Weaviate docs pages, and does moving the other
  languages' examples off the page reduce that?
---

# investigate/index-import-pages-python

[`investigate/index-import-pages`](index-import-pages.md) with Python as the
only language. The pages, scenario, items, and Oracle recommendations are the
same; see that page for the design and the Go disagreement between the pages.

In `index-import-pages`, the
[`markdown-docs-iter2`](../../../treatments/markdown-docs-iter2/README.md)
Agents fetched the code page of every language, so the split added fetches
and turns. With Python only, iter2's pages hold every example the agent
needs inline, so this Task measures the split for the reader it favours. The
baseline, [`markdown-docs-iter1`](../../../treatments/markdown-docs-iter1/README.md),
and `markdown-docs-iter2` prompts differ only in their URLs.

## Boundary conditions

### Prompt

> We're building product search with Weaviate over about 5 million product
> descriptions, embedded through Weaviate's `text2vec-openai` module with
> OpenAI's `text-embedding-3-small` (1,536 dimensions). Search must handle
> high query throughput at low latency, and we want to reduce the vector
> index's memory use without losing much recall. We'll import the catalog
> from a JSONL file with one product per line (`title` and `description`),
> and we'll use Python.
>
> Read these pages of the Weaviate docs, and no others:
>
> - https://docs.weaviate.io/weaviate/concepts/vector-index
> - https://docs.weaviate.io/weaviate/concepts/vector-quantization
> - https://docs.weaviate.io/weaviate/concepts/data-import
> - https://docs.weaviate.io/weaviate/configuration/compression/rq-compression
> - https://docs.weaviate.io/weaviate/manage-objects/import
>
> Use only these pages: don't fetch other URLs, install packages, or run
> code to check your answer.
>
> From them, recommend the vector index, compression, and import method for
> this project, and write the Python code. Write your findings to
> `/app/findings.json` in the format described in `WORKSPACE.md`, citing the
> page each answer came from.

### Workspace

- `WORKSPACE.md`: the `findings.json` format, as in `index-import-pages`, with
  a `code` object holding only a `python` string.

### Initial state

Nothing is running.

## Observations

`snapshot.py` records the submitted `findings.json`. The code is not run.
`weval.json`'s `usage.urls` shows whether the agent kept to the five pages.

## Checks

Neither the recommendations nor the code are scored.

| Check | Tier | Validation |
|---|---|---|
| `findings-file` | REQUIRED | `/app/findings.json` is a JSON object with every documented item, each with an `answer` string and a `sources` list, and a `python` code string for `vector_index` and `batch_import`. |

## Calibration

Variants are in `tests/test_investigate_index_import_pages_python_check.py`.
The Oracle's answers are `index-import-pages`'s, with only the Python code.

| Variant | Fails | Models |
|---|---|---|
| `missing_file` | every check | No `findings.json` was written. |
| `missing_item` | `findings-file` | `compression` is absent. |
| `missing_language` | `findings-file` | `batch_import` has no Python code. |
