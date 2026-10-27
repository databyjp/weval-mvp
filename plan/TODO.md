# TODO

Remaining work, roughly in order. Delete items when done.

## Re-score tooling

- `weval check` only prints, so re-score results live in analysis files that
  record the date and commit (`analysis/2026-10-27-rescore.md`). If
  re-scoring becomes routine, consider having `weval check` print the commit
  and date itself, or write a file the report can read.
- The four `investigate/stack-recommendation` Trials record a Task path that
  no longer exists; re-score them with
  `--task tasks/investigate/db-recommendation`.

## Generate the Task catalog

- Add a generator that writes `docs/tasks/README.md` from the Task pages and
  `check.py`: each Task's path and link, motivation, prompt, and checks with
  tiers and docstrings.
- Mark the file clearly as generated, with a do-not-edit line that names the
  generator.
- Add a test that regenerates the catalog and fails on a diff.
- Replace the hand-maintained Tasks line in `docs/introduction.md` with a link
  to the catalog.

## Add colliding SKUs to build/ecommerce-search

- The catalog has no SKU sharing a token with `ZXQ-9917`, so
  `exact-sku-retrieval` passes under word tokenization and can't detect the
  fault behind "exact SKU lookup".
- Add colliding SKUs to `products.json`, then review
  `PAGINATION_REFERENCE_SIZE = 24` and `catalog-ingestion`'s count.
- Costs one Modal Oracle run to regenerate
  `tests/fixtures/build-ecommerce-search-oracle-snapshot.json`.

## investigate/current-practices

Built, and the Oracle passes on local Docker. Next: run Pi Trials (`--local`
works for this Task) and read their `usage` in `weval.json`. The spec is
`docs/tasks/investigate/current-practices.md`.

Answer criteria cover the versions and the vector configuration API; see the
Task page. Still open:

- Criteria for `deployment` and `search`. Candidate expected answers are in
  the Task page's Calibration table, and need re-checking against the docs
  first.
- Checks over the logs, such as "the agent fetched the page it cited". These
  need host-side scoring in `finalize()`, which makes `weval.json` the
  authoritative result and can disagree with Harbor's in-environment reward.
- Possible gaps in `usage.urls`, to confirm from real Trial output:
  - pages read through `get_search_content` appear as a search-result ID,
    not a URL, so they may be missing; they may be recoverable from the
    tool results;
  - Claude Code's `WebSearch` results list URLs only in the tool results,
    so `usage.urls` holds the pages fetched, not the results seen;
  - URLs built in shell keep unexpanded variables, such as
    `...releases?per_page=100&page=$page`.

Observed in the first three local Pi Trials
(`experiment-outputs/20261016-100754__investigate__current-practices__pi-glm-5.3-flash`):

- All three read `weaviate.io/llms.txt`. Many fetched legacy
  `weaviate.io/developers/weaviate/...` paths; one fetched `.md` versions of
  `docs.weaviate.io` pages. Both matter for the docs-site comparison.
- One Trial made 36 `get_search_content` calls, so the gap below is real.
- Regex text in bash commands is extracted as URLs, such as
  `https://docs.weaviate.io/[a-z0-9/._-`.
- The agents' answers disagree with the Oracle's in places: all three say
  HNSW ships with RQ8 quantization by default, and that Weaviate Cloud is the
  first deployment recommendation. The Oracle's answers came from summaries
  of individual docs pages. Before writing criteria, re-check each expected
  answer against the docs, including `llms.txt`; where pages disagree, that
  is a possible Weaviate gap.

The `weaviate-docs` Treatment measures token use here, with the REQUIRED
answer checks as a correctness guard.

## Claude Code binary on GitHub Actions runners

Modal Trials read Claude Code from the `weval-claude-code` Volume. If Trials
run with `--local` on GitHub Actions runners, keep the host cache between
workflow runs instead, so runners do not download from `downloads.claude.ai`:

- add an `actions/cache` step for `~/.cache/weval/claude-code`, keyed on
  `hashFiles('agents.toml')`;
- check that the runner has the memory for Harbor's `apt-get install nodejs
  npm procps`, which exited 137 in a local Trial on a laptop;
- download once per workflow: the host lock in `cached_binary` does not reach
  across matrix jobs, and `actions/cache` saves only when a job ends. Add a
  `weval prepare` command (download every version in `agents.toml`, and
  publish it to the Volume for Modal runs) and run it in a setup job that the
  matrix jobs list under `needs:`.

An Experiment runner, when one exists, should call the same preparation once
before it starts its runs.

## Compare docs-site versions

Run Tasks against different versions of the docs site to see whether changes
reduce token use. Needs the `usage` metrics in `weval.json` and a way to point
the agent's fetches at a site variant.

## Smaller items

- `docs/tasks/resolve/sku-search.md`: "Boundary Conditions" and "Intial
  State" headings (case, typo) and the misindented nested bullet.
- Motivations for `build/ecommerce-search`, `deploy/local-instance`, and
  `deploy/document-search-upgrade` are agent drafts; rewrite them.
- Decide whether `motivation` should also cite evidence that the scenario
  matters, as Supabase's evals do.
- The four per-Task test files load `check.py` without
  `assert spec and spec.loader`; pyright may flag them.
- Optional: add "unless the maintainer has said more will" to the
  `AGENTS.md` rule about adding a shared abstraction when three Tasks need it.
