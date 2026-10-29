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

`snapshot.py` records the submitted `findings.json`. The code is not run.

## Checks

Neither prose answers nor code are scored. The Task records what agents
answer and which pages they read, for comparing docs-site variants by tokens.
Text patterns over client syntax were too brittle to score the code: valid
variants, such as Go v5's hybrid builder, failed them.

| Check | Tier | Validation |
|---|---|---|
| `findings-file` | REQUIRED | `/app/findings.json` is a JSON object with every documented item, each with an `answer` string and a `sources` list, and `python`, `typescript`, and `go` code strings for `config_ingestion` and `search`. |

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
| `missing_language` | `findings-file` | `config_ingestion` has no TypeScript code. |
