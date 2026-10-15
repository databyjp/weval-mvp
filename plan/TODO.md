# TODO

Remaining work, roughly in order. Delete items when done.

## Re-score retained Trials

- Run `uv run weval check` on every retained Trial in `experiment-outputs/`
  against the current checks. Retained Pi Trials of `resolve/sku-search` will
  mostly fail now that `sku-field-tokenization` is REQUIRED.
- Classify each failure as an agent gap, Weaviate gap, scorer bug, or Task
  defect (`AGENTS.md`, "Failed checks are findings").
- Write the results to a separate analysis file, never into the retained
  Trial. `weval check` only prints, so the file records the date and the
  commit whose `check.py` scored each Trial.
- If re-scoring becomes routine, consider having `weval check` print the
  commit and date itself.

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

## New Task: latest version and best practices

Ask an agent to find the latest Weaviate version and current best practices.
The question is whether it consults the canonical docs. A PREFERRED criterion
records the tokens consumed, as a baseline to optimise later.

Open design questions:

- Stage: this fits none of `build`, `deploy`, or `resolve`. A new stage, such
  as `investigate`, goes in `AGENTS.md` and `STAGES` in `tests/test_verify.py`.
- Deliverable: what the agent writes (for example, an answer file in `/app`)
  so `snapshot.py` can capture it.
- Evidence of investigation: which canonical sources count, and where the
  check reads them from. Pi's transcript records fetches, but `check.py`
  reads only the snapshot, which the verifier takes inside the Trial
  environment.
- Token use: Harbor records `n_input_tokens`, `n_cache_tokens`,
  `n_output_tokens`, and `cost_usd` in `result.json` after the Trial, outside
  the snapshot. Scoring it means either reading `result.json` in
  `finalize()` or reporting it as a metric rather than a check. Either is a
  framework change, so ask first.
- A pass threshold, or a note-only check that always passes and records the
  count, as `deploy/local-instance`'s `auth-posture` does.

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
