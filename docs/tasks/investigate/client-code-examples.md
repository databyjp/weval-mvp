---
motivation: >
  Can an agent find the current recommended practice in the Weaviate docs,
  with Python, TypeScript, and Go code that uses each client's current API?
  The docs show each language in a tab, and only the default Python tab is
  visible in the HTML.
---

# investigate/client-code-examples

The workspace holds only a description of the findings file. Nothing is
running. The agent is asked for the recommended way to deploy, to create a
collection with a vectorizer and import data, and to search, with code in
Python, TypeScript, and Go for the last two.

The docs pages serve every language's code in the HTML but hide the
non-default tabs (`style=display:none aria-hidden=true`), so the code an agent
receives depends on how its fetch tool treats hidden elements. The
[`markdown-docs-staging`](../../../treatments/markdown-docs-staging/README.md)
Treatment points the agent at a staging docs site that serves every tab as
Markdown.

## Boundary conditions

### Prompt

> We're starting a new project with Weaviate and will use it from Python,
> TypeScript, and Go. Starting from the Weaviate docs at
> https://docs.weaviate.io/weaviate, find the recommended way to do each item
> listed in `WORKSPACE.md`, with code in each language. Write your findings to
> `/app/findings.json` in the format described there, citing the page each
> answer came from.

### Workspace

- `WORKSPACE.md`: the `findings.json` format. It has three items
  (`deployment`, `config_ingestion`, `search`), each with an `answer` string
  and a `sources` list of URLs. `config_ingestion` and `search` also have a
  `code` object with `python`, `typescript`, and `go` strings. It names no
  client API, client version, or search type.

### Initial state

Nothing is running.

## Observations

`snapshot.py` records the submitted `findings.json`. The code is checked as
text; it is not run.

## Checks

Prose answers are not scored. Each code check is a detection check: the prompt
asks for code, not for an API or client version.

| Check | Tier | Validation |
|---|---|---|
| `findings-file` | REQUIRED | `/app/findings.json` is a JSON object with every documented item, each with an `answer` string and a `sources` list, and `python`, `typescript`, and `go` code strings for `config_ingestion` and `search`. |
| `python-current-vector-config` | REQUIRED | `config_ingestion`'s Python code uses `Configure.Vectors` or `vector_config=`. The legacy API is `vectorizer_config=Configure.Vectorizer`, replaced in client 4.16. |
| `typescript-current-vector-config` | REQUIRED | `config_ingestion`'s TypeScript code calls `vectors.<module>()`. The legacy API is `configure.vectorizer`, replaced in client 3.8. |
| `go-v6-client` | REQUIRED | `config_ingestion`'s and `search`'s Go code use the v6 collections API (`.Collections.<method>(` or the `weaviate-go-client/v6` module) and no v5 call (`.Schema()`, `.GraphQL()`, `.Batch().ObjectsBatcher(`, or a v4/v5 module). The docs show v5 and v6 tabs side by side. |
| `hybrid-search-code` | PREFERRED | `search`'s code runs a hybrid query in every language. The docs recommend hybrid search as the starting point. |

## Calibration

Variants are in `tests/test_investigate_client_code_examples_check.py`. The
Oracle writes the docs' own Python, TypeScript, and Go (v6) examples from the
vector configuration, batch import, and hybrid search pages, with these
answers:

| Item | Oracle answer | Source |
|---|---|---|
| `deployment` | Docker for local development; Kubernetes or Weaviate Cloud for production. | `docs.weaviate.io/deploy` |
| `config_ingestion` | A named vector from `Configure.Vectors` (`configure.vectors` in TypeScript, the `Vectors` map in Go v6); server-side batch import. | `docs.weaviate.io/weaviate/manage-collections/vector-config`, `.../manage-objects/import` |
| `search` | Hybrid search as the starting point. | `docs.weaviate.io/weaviate/concepts/search`, `.../search/hybrid` |

| Variant | Fails | Models |
|---|---|---|
| `missing_file` | every check | No `findings.json` was written. |
| `missing_item` | `findings-file` | `deployment` is absent. |
| `missing_language` | `findings-file`, `typescript-current-vector-config` | `config_ingestion` has no TypeScript code. |
| `python_legacy_vectorizer` | `python-current-vector-config` | Uses `vectorizer_config=Configure.Vectorizer`. |
| `typescript_legacy_vectorizer` | `typescript-current-vector-config` | Uses `configure.vectorizer`. |
| `go_v5_client` | `go-v6-client` | Creates the collection with `Schema().ClassCreator()`. |
| `go_mixed_clients` | `go-v6-client` | Creates a v6 collection, then imports with the v5 `ObjectsBatcher`. |
| `go_rest_calls` | `go-v6-client`, `hybrid-search-code` | Calls the REST API with `net/http` instead of a client. |
| `typescript_vector_search` | `hybrid-search-code` | Searches with `nearText`. |
