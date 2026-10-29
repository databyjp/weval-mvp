---
motivation: >
  How many tokens does an agent spend finding the current Weaviate versions
  and recommended practices when pointed at the docs, and does serving the
  docs as Markdown reduce that?
---

# investigate/docs-token-usage

A copy of [`investigate/current-practices`](current-practices.md) whose
prompt names the docs site to start from, so that a Treatment can swap in
another docs site and compare token usage. The workspace, snapshot, and Oracle
are the same; see that page for what `snapshot.py` and `weval.json` record.

The [`markdown-docs-staging`](../../../treatments/markdown-docs-staging/README.md)
Treatment replaces the prompt with one that points at a staging docs site
serving Markdown pages.

## Boundary conditions

### Prompt

> We're starting a new project with Weaviate. Starting from the Weaviate docs
> at https://docs.weaviate.io/weaviate, find the latest Weaviate versions to
> use, and the recommended way to do each item listed in `WORKSPACE.md`.
> Write your findings to `/app/findings.json` in the format described there,
> citing the page each answer came from.

### Workspace

- `WORKSPACE.md`: the `findings.json` format, as in
  `investigate/current-practices`.

### Initial state

Nothing is running.

## Checks

`deployment` and `search` answers are not scored. Every check is a
`REQUIRED` check of `investigate/current-practices`. Its `PREFERRED`
`canonical-sources` check is left out: Treatment Trials cite the staging
site, which is not a Weaviate-owned host, so the check would fail by
construction and add noise to the Treatment comparison.

| Check | Tier | Validation |
|---|---|---|
| `findings-file` | REQUIRED | `/app/findings.json` is a JSON object with every documented item, each with an `answer` string and a `sources` list. |
| `weaviate-version-latest` | REQUIRED | `weaviate_version` names the latest stable Weaviate release at verify time, including its patch. |
| `python-client-version-latest` | REQUIRED | `client_library_versions` names the latest `weaviate-client` release on PyPI at verify time, including its patch. |
| `current-vector-config` | REQUIRED | `config_ingestion` names `vector_config`, `Configure.Vectors`, or named vectors. |

## Calibration

The checks are copied unchanged from `investigate/current-practices`, whose
calibration variants cover them. The Oracle is the same and passes every
check.
