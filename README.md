# weval

Runs Weaviate coding Tasks against coding agents on Modal through
Harbor (`harbor[modal]`), snapshots the stack each
agent leaves running, and scores it check by check.

## Setup

```sh
uv sync
```

Create `.env` with `OPENROUTER_API_KEY`, `MODAL_TOKEN_ID`, and
`MODAL_TOKEN_SECRET`. Git ignores it, and after each run weval replaces any
of these values found in retained output with `<redacted:NAME>`.

## Use

```sh
# One Oracle Trial (runs solution/solve.sh; checks the Task itself)
uv run --env-file .env weval run tasks/greenfield-ecommerce-search --condition oracle

# Three Pi + GLM Trials
uv run --env-file .env weval run tasks/greenfield-ecommerce-search --condition pi-glm-5.3-flash -n 3

# Re-score a retained Trial with the Task's current check.py
uv run weval check experiment-outputs/<run>/job/<trial>
```

Each run writes `experiment-outputs/<timestamp>-<task>-<condition>/`. Each
Trial in `job/` has a `weval.json` with its status, Condition, and per-check
results.

Tasks live in `tasks/`; Conditions in `conditions.toml`. See
[`AGENTS.md`](AGENTS.md) for writing Tasks and reading results, and
[`GLOSSARY.md`](GLOSSARY.md) for terms.
