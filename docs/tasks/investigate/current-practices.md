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
verify time: the Python client from PyPI, and Weaviate from GitHub's releases
API, or from the releases Atom feed when the API refuses. The API's
unauthenticated limit is per IP, and Modal Trials share egress IPs with agents
that call the same API; the limit cost 3 of 15 retained Modal Trials their
Weaviate release. Latest releases change, so the checks compare answers with
the values from the Trial's own time.

`weval.json` records, for every Trial of every Task, the tokens and cost from
Harbor's `result.json`, and the URLs and search queries in the agent's tool
calls from `trajectory.json`. URLs come from tool-call arguments, so a page
read through search results without its own fetch is not listed.

## Checks

`deployment` and
`search` answers are not scored: their expected answers need judgment, and
the Oracle's came from summaries of single docs pages that baseline Trials
disagree with.

| Check | Tier | Validation |
|---|---|---|
| `findings-file` | REQUIRED | `/app/findings.json` is a JSON object with every documented item, each with an `answer` string and a `sources` list. |
| `weaviate-version-latest` | REQUIRED | `weaviate_version` names the latest stable Weaviate release at verify time, including its patch. |
| `python-client-version-latest` | REQUIRED | `client_library_versions` names the latest `weaviate-client` release on PyPI at verify time, including its patch. |
| `current-vector-config` | REQUIRED | `config_ingestion` names `vector_config`, `Configure.Vectors`, or named vectors. Detection: the prompt asks for the recommended way to configure, not for an API, and the legacy path is `vectorizer_config=Configure.Vectorizer`. |
| `canonical-sources` | PREFERRED | Every answer cites a source, and every source is on a Weaviate site (`weaviate.io` and its subdomains, `github.com/weaviate`, `api.github.com/repos/weaviate`) or an official client's package registry, including its API host such as `registry.npmjs.org`. |

A version check fails when its release could not be looked up at verify time;
classify that as an infrastructure failure.

## Calibration

Variants are in `tests/test_investigate_current_practices_check.py`. The
Oracle looks up the latest releases at run time and writes the answers below,
each citing the page it came from.
`deployment` and `search` are not scored.

| Item | Oracle answer | Source |
|---|---|---|
| `deployment` | Docker for local development; Kubernetes or Weaviate Cloud for production. | `docs.weaviate.io/deploy` |
| `config_ingestion` | `vector_config=Configure.Vectors.<module>()` (Python client 4.16 and later) and an HNSW index, starting with rotational quantization (RQ) for compression; server-side batch import. | `docs.weaviate.io/weaviate/manage-collections/vector-config`, `.../best-practices`, `.../manage-objects/import` |
| `search` | Hybrid search as the starting point. | `docs.weaviate.io/weaviate/concepts/search` |

| Variant | Fails | Models |
|---|---|---|
| `missing_file` | every check | No `findings.json` was written. |
| `missing_item` | `findings-file` | `search` is absent. |
| `answer_not_string` | `findings-file`, `current-vector-config` | An answer is a nested object. |
| `server_patch_behind` | `weaviate-version-latest` | Names 1.40.1, not the latest 1.40.2. |
| `server_minor_only` | `weaviate-version-latest` | Names 1.40 without a patch. |
| `server_version_prefix` | `weaviate-version-latest` | The latest release is 1.40.20; the answer names 1.40.2. |
| `server_release_unavailable` | `weaviate-version-latest` | The release lookup failed at verify time. |
| `client_version_behind` | `python-client-version-latest` | Names an older Python client. |
| `legacy_vectorizer_config` | `current-vector-config` | Recommends `vectorizer_config=Configure.Vectorizer`. |
| `prose_without_api` | `current-vector-config` | Describes configuration without naming the vector API. |
| `uncited_answer` | `canonical-sources` | `search` has no sources. |
| `blog_source` | `canonical-sources` | `search` cites a blog post. |
| `other_github_owner` | `canonical-sources` | `search` cites another owner's repository through the GitHub API. |
