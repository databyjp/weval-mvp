# First Treatment runs, 2026-10-27

Each Treatment arm ran 5 Trials with `claude-code-sonnet-5.5`, default
prompt variant, on Modal, against a baseline arm of 5 run the same day. Both
Treatments are agent drafts committed in `a7ec196`; checks are those at
`7eb3170`.

| Arm | Run | Passed | Mean cost (USD) | Mean output tokens | Mean uncached input tokens | Mean tool calls |
|---|---|---|---|---|---|---|
| ecommerce-search baseline | `20261027-114144` | 0/5 | 0.084 | 4,164 | 12,136 | 6.4 |
| ecommerce-search + `weaviate-best-practices` | `20261027-114648` | 5/5 | 0.088 | 4,529 | 11,341 | 7.2 |
| current-practices baseline | `20261027-101924` | 0/5 | 0.113 | 3,961 | 62,459 | 9.8 |
| current-practices + `weaviate-docs` | `20261027-114648` | 3/5 | 0.089 | 2,875 | 19,180 | 6.6 |

Uncached input is `n_input_tokens - n_cache_tokens`. The four runs cost
$1.87 in total.

The report's Treatments tab pools every retained baseline run of the same
Task, prompt variant, and Agent, so its baseline rows also include the
20 and 21 October runs (7 Trials each). This note compares the same-day
arms only.

## build/ecommerce-search with weaviate-best-practices

Every Treatment Trial loaded the skill (one `Skill` call each), pinned
Weaviate 1.40.2, and configured `vector_config=Configure.Vectors.text2vec_transformers`.
All five also passed both PREFERRED checks, `sku-category-field-tokenization`
and `hybrid-query`.

Every baseline Trial failed `weaviate-managed-vectorization` with the legacy
collection-level vectorizer, on Weaviate 1.27.0, 1.28.4, or 1.30.0. None of
them fetched a URL. All five failed `hybrid-query`, and two failed
`sku-category-field-tokenization`.

Cost and token use are within 10% of the baseline, so the skill changed
the outcome without adding cost.

The skill's guidance lines up closely with this Task's checks: it names
`vector_config`, `field` tokenization for codes, and hybrid search. The
README calls it general guidance, but this run doesn't show whether a skill
that covers this Task's checks less directly would have the same effect. A
second Task that the skill doesn't target would show whether it misleads
elsewhere.

## investigate/current-practices with weaviate-docs

No Treatment Trial used `WebFetch` or `WebSearch`. Each loaded the skill and
read the pages with `cat`, `head`, and `grep`. The answers cite the pages'
`Source:` URLs.

Compared with the baseline, the Treatment cost 21% less per Trial, wrote
27% fewer output tokens, and read 69% fewer uncached input tokens. It also
passed more Trials:

- `current-vector-config` passed 5/5 against 1/5. `vector-config.md` opens
  with the API change notice and a `vector_config=Configure.Vectors` example.
- `weaviate-version-latest` passed 5/5, as in the baseline. Of the twelve
  pages, only `docker-installation.md` names 1.40.2. At least two answers
  also noted that the release-notes table of supported versions says
  `v1.40.0`.
- `python-client-version-latest` passed 3/5 against 2/5. The three Trials
  that read `client-libraries-python.md` named 4.24.1 from its first line.
  The two whose tool results never included that line gave "4.24.x";
  `FSBariP` searched the page with `grep` patterns that missed it
  (`weval check` reports this as "not seen"). This is the Weaviate gap in
  `analysis/2026-10-27-current-practices-baseline.md`: the most-read page
  gives the minor line, and the patch is one page deeper.

## Candidate Weaviate gaps

From the docs pages fetched on 2026-10-27:

- `weaviate/release-notes`: the supported-versions table gives `v1.40.0` as
  the latest 1.40 patch while 1.40.2 was out, and the client table lists
  Python by minor line only.
- `deploy/installation-guides/docker-installation`: "Set `vectorizer` to
  `text2vec-transformers` in each collection definition" describes the
  legacy collection-level vectorizer, the form every failing ecommerce-search
  baseline Trial used.

## Limits

Five Trials per arm with one Agent. The `weaviate-best-practices` result is
5/5 against 0/7 Sonnet baseline Trials on three days, which is unlikely to
be variance. The `weaviate-docs` pass-rate change hinges on whether a
Trial opens one page, so it needs more Trials before it means more than
the usage change.
