---
motivation: >
  Can an agent find the current Weaviate versions and recommended practices in
  the canonical docs, and how many tokens does it spend doing so?
---

# investigate/current-practices

The workspace holds only a description of the findings file. Nothing is
running. The agent is asked to find the latest Weaviate versions and the
recommended way to deploy, configure and ingest, and search, citing its
sources.

## Boundary conditions

### Prompt

> We're starting a new project with Weaviate. Find the latest Weaviate
> versions to use, and the recommended way to do each item listed in
> `WORKSPACE.md`. Write your findings to `/app/findings.json` in the format
> described there, citing the page each answer came from.

The [prompt variants](../../reference.md#prompt-variants) in `prompts/`
replace the first sentence with a use case and are otherwise identical:

| Variant | In place of the first sentence |
|---|---|
| `help-chatbot` | We're building a customer-facing help chatbot with Weaviate as the vector database. |
| `shopping-search` | We're building an e-commerce store with Weaviate as the vector database. |
| `legal-archive` | We're building a search app to look through a very large archive of legal documents with Weaviate as the vector database. Being cost-effective is important to us. |

### Workspace

- `WORKSPACE.md`: the `findings.json` format. It has five items
  (`weaviate_version`, `client_library_versions`, `deployment`,
  `config_ingestion`, `search`), each with an `answer` string and a `sources`
  list of URLs. It names each item without suggesting answers, and leaves
  open which client libraries to cover and what "configure" includes.

### Initial state

Nothing is running.

## Observations

`snapshot.py` records the submitted `findings.json` and the latest releases at
verify time: Weaviate from GitHub's releases API and the Python client from
PyPI. Latest releases change, so later criteria need the values from the
Trial's own time.

`weval.json` records, for every Trial of every Task, the tokens and cost from
Harbor's `result.json`, and the URLs and search queries in the agent's tool
calls from `trajectory.json`. URLs come from tool-call arguments, so a page
read through search results without its own fetch is not listed.

## Checks

Criteria for the answers and their sources are deferred until the
observations above have been seen in real Trials. Every variant is scored on
the checks below; `PROMPT_VARIANT_REQUIRED` and `PROMPT_VARIANT_PREFERRED` in `check.py` are
empty placeholders for checks that differ by use case.

| Check | Tier | Validation |
|---|---|---|
| `findings-file` | REQUIRED | `/app/findings.json` is a JSON object with every documented item, each with an `answer` string and a `sources` list. |

## Calibration

Variants are in `tests/test_investigate_current_practices_check.py`. The
Oracle looks up the latest releases at run time and writes the answers below,
each citing the page it came from. They are placeholders that pass
`findings-file`, the same for every prompt variant, until the criteria are
designed.

| Item | Oracle answer | Source |
|---|---|---|
| `deployment` | Docker for local development; Kubernetes or Weaviate Cloud for production. | `docs.weaviate.io/deploy` |
| `config_ingestion` | `vector_config=Configure.Vectors.<module>()` (Python client 4.16 and later) and an HNSW index, starting with rotational quantization (RQ) for compression; client-side batch import. | `docs.weaviate.io/weaviate/manage-collections/vector-config`, `.../best-practices`, `.../manage-objects/import` |
| `search` | Hybrid search as the starting point. | `docs.weaviate.io/weaviate/concepts/search` |

| Variant | Fails | Models |
|---|---|---|
| `missing_file` | `findings-file` | No `findings.json` was written. |
| `missing_item` | `findings-file` | `search` is absent. |
| `answer_not_string` | `findings-file` | An answer is a nested object. |
