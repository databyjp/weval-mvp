---
motivation: >
  Can an agent find the current Weaviate versions and recommended practices in
  the canonical docs, and how many tokens does it spend doing so?
---

# investigate/current-practices

The workspace holds only a description of the findings file. Nothing is
running. The agent is asked to find the latest Weaviate versions and the
recommended way to deploy, vectorize, index, and search, citing its sources.

## Boundary conditions

### Prompt

> We're starting a new project with Weaviate. Find the latest Weaviate
> versions to use, and the recommended way to do each item listed in
> `WORKSPACE.md`. Write your findings to `/app/findings.json` in the format
> described there, citing the page each answer came from.

The [prompt variants](../../reference.md#prompt-variants) in `prompts/` name a
use case in the first sentence and are otherwise identical:

| Variant | First sentence |
|---|---|
| `help-chatbot` | We're starting a new project with Weaviate: a customer-facing help chatbot. |
| `shopping-search` | We're starting a new project with Weaviate: the product search engine for an e-commerce store. |
| `legal-archive` | We're starting a new project with Weaviate: cost-effective search over a very large archive of legal documents. |

### Workspace

- `WORKSPACE.md`: the `findings.json` format. It has six items
  (`weaviate_version`, `python_client_version`, `deployment`,
  `vectorization`, `indexing`, `search`), each with an `answer` string and a
  `sources` list of URLs. It names each item without suggesting answers.

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
each citing the page it came from.

| Item | Oracle answer | Source |
|---|---|---|
| `deployment` | Docker for local development; Kubernetes or Weaviate Cloud for production. | `docs.weaviate.io/deploy` |
| `vectorization` | `vector_config=Configure.Vectors.<module>()`, the API since Python client 4.16. | `docs.weaviate.io/weaviate/manage-collections/vector-config` |
| `indexing` | HNSW for most cases; rotational quantization (RQ) as a starting point for compression. | `docs.weaviate.io/weaviate/best-practices` |
| `search` | Hybrid search as the starting point. | `docs.weaviate.io/weaviate/concepts/search` |

| Variant | Fails | Models |
|---|---|---|
| `missing_file` | `findings-file` | No `findings.json` was written. |
| `missing_item` | `findings-file` | `search` is absent. |
| `answer_not_string` | `findings-file` | An answer is a nested object. |
