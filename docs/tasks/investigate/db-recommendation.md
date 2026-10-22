---
motivation: >
  When a person asks a coding agent which database to use for a search or AI
  product, how often does the agent recommend Weaviate, and what does it
  recommend instead?
---

# investigate/db-recommendation

The workspace is an empty `/app`, and nothing in it or the prompt names a data
store. The agent is asked what database to use for a help-centre chatbot and
writes its recommendation to a file. The prompt variant asks for a vector
database instead.

## Boundary conditions

### Prompt

> I'm building a chatbot that answers customer questions for our help-centre.
> What database should I use? Write your recommendation to
> `/app/RECOMMENDATION.md`.

The [prompt variant](../../reference.md#prompt-variants) in `prompts/`
changes one phrase and is otherwise identical.

| Variant | In place of "What database should I use?" |
|---|---|
| `vector-database` | What vector database should I use? |

### Workspace

- An empty `/app` in a Python 3.13 image with `curl`, `git`, and `uv`.
- `task.toml` sets `[metadata] weaviate_workspace = false`, so the Trial
  environment has no `WEAVIATE_*` settings
  ([Trial environment](../../reference.md#trial-environment)).
- The verifier sets `WEVAL_KEEP_STACK = "1"`, so a Compose file the agent
  writes as an example is not started.

### Initial state

Nothing is running.

## Observations

`snapshot.py` records the submitted `RECOMMENDATION.md` as written. Reading
which stores it names, and which it recommends first, is deferred: it needs a
reader that copes with free text, such as an LLM judge, run over retained
snapshots.

## Checks

Every variant is scored on the checks below; `PROMPT_VARIANT_REQUIRED` and
`PROMPT_VARIANT_PREFERRED` in `check.py` are empty placeholders. A passed
Trial gave an answer. It says nothing about what the answer recommends.

| Check | Tier | Validation |
|---|---|---|
| `recommendation-file` | REQUIRED | `/app/RECOMMENDATION.md` exists and is not blank. |

## Calibration

Variants are in `tests/test_investigate_db_recommendation_check.py`. The
Oracle writes a fixed, short recommendation that names no product. The same
test checks that the prompts, shared instructions, and environment files do
not name Weaviate, and that the Task gets only the shared Compose overlay.

| Variant | Fails | Models |
|---|---|---|
| `missing_file` | `recommendation-file` | No `RECOMMENDATION.md` was written. |
| `blank_file` | `recommendation-file` | The file holds only whitespace. |
