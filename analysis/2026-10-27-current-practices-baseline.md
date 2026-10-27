# investigate/current-practices baseline, 2026-10-27

Run `20261027-101924__investigate__current-practices__claude-code-sonnet-5.5`:
5 Trials, default prompt variant, Modal, scored by the checks at `7eb3170`.
It is the baseline arm for the `weaviate-docs` Treatment.

| Trial | Failed REQUIRED | Cost (USD) | Output tokens | URLs |
|---|---|---|---|---|
| `hANvYSV` | `python-client-version-latest` | 0.083 | 3,108 | 5 |
| `JtwVga5` | `python-client-version-latest`, `current-vector-config` | 0.085 | 4,000 | 7 |
| `HUvNZF2` | `python-client-version-latest`, `current-vector-config` | 0.088 | 3,429 | 6 |
| `LrQKZKu` | `current-vector-config` | 0.144 | 4,657 | 10 |
| `SEqcL3X` | `current-vector-config` | 0.166 | 4,613 | 11 |

The rows are in the order of each Trial's `weval.json`. Total cost was
$0.566. At verify time the latest releases were Weaviate 1.40.2 and
`weaviate-client` 4.24.1. Each snapshot took both from the GitHub API and
PyPI, so the Atom-feed fallback was not needed. Every Trial named 1.40.2 and
passed `weaviate-version-latest`.

## python-client-version-latest: agent gap, possible Weaviate gap

The three failing answers give "Python 4.24.x". They took it from the 1.40
compatibility table on the docs release-notes page, which lists client
versions by minor line. The two Trials that also checked PyPI named 4.24.1.
`JtwVga5` wrote "check PyPI and npm for the exact patch" and stopped there.
PyPI published 4.24.1 on 2026-10-26 and 4.24.0 on 2026-10-21.

The docs table answering with a minor line is a candidate Weaviate gap: it is
the page agents land on, and it stops them one step short. `WORKSPACE.md`
describes the item as "the corresponding Weaviate client versions", which can
be read as the compatible line rather than the latest release. The prompt asks
for "the latest Weaviate versions to use", so I classified it as an agent gap.
The check stays as it is.

## current-vector-config: agent gap

Four answers describe collection configuration without naming the vector
API:
- `JtwVga5`: "choose a vectorizer module (e.g. text2vec-openai)".
- `HUvNZF2`, `LrQKZKu`, `SEqcL3X`: "vectorizer/vector config" or "vectorizer/vector index config".

None recommends the legacy `vectorizer_config`. `hANvYSV` names
`vector_config=Configure.Vectors.text2vec_weaviate()`. Both retained Sonnet
Trials of the default prompt variant from 20 and 21 October also named
`Configure.Vectors`. At n=2 and n=5, that difference may be variance.

## For the Treatment comparison

The baseline passes 0 of 5, so `weaviate-docs` can move the pass rate as
well as usage. The Treatment's pages include `release-notes.md` and
`client-libraries-python.md`. If the release-notes copy carries the same
minor-line table, the Treatment may reproduce the client-version failure.
