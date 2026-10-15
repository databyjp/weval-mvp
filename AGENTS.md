# weval development

weval runs Weaviate coding Tasks against agent harnesses and keeps what is
needed to analyse each Trial. Most work here should be writing Tasks and
reading results, not growing the framework. Use [`GLOSSARY.md`](GLOSSARY.md)
as the domain language.

## Layout

- `tasks/<name>/`: one Task each (see below).
- `agents.toml`: named Agents (harness, version, model).
- `src/weval/run.py`: builds the Harbor package, runs it on Modal, writes `weval.json`.
- `src/weval/verify.py`: shared verifier that runs inside the Trial environment.
- `src/weval/shared-instructions.md`: Trial-environment notes appended to every
  Task's prompt when it is packaged.
- `src/weval/shared-compose.yaml`: Compose overlay applied to every Trial
  environment: the Trial network, `WEAVIATE_*` settings, and Docker socket.
- `src/weval/harnesses/<harness>.py`: Harbor agent config, expected logs, and
  any harness-specific setup (for example, Pi's pinned `pi-web-access`).
- `experiment-outputs/`: retained runs (git-ignored).

Keep the framework small enough to read in one sitting. Prefer plain functions
and dicts. Add a shared abstraction only when three Tasks need it. Handle
cases that Trials have shown, not anticipated ones
([ADR 0001](architecture/adr/0001-handle-observed-cases.md)). If a change
makes the framework noticeably larger, ask first.

## Writing a Task

A Task is a directory that runs without framework changes:

| File | Purpose |
|---|---|
| `instruction.md` | What the agent is told (Harbor's file name for the prompt). Packaging appends `src/weval/shared-instructions.md`. |
| `task.toml` | Harbor task config: timeouts, `/app` artifact, healthcheck, verifier env. |
| `environment/` | Harbor environment: `Dockerfile`, starter app, fixtures, and an optional Compose overlay for Task-specific settings such as a healthcheck. |
| `solution/solve.sh` | The Oracle solution. It must pass every check. |
| `snapshot.py` | `snapshot(app_url) -> dict`: dump the live state to JSON. `app_url` is `None` without an app. |
| `check.py` | `REQUIRED` and `PREFERRED` lists of check functions over the snapshot. |

`verify.py` starts the submitted Compose stack, calls `snapshot()`, and scores
the result. Set these in `[verifier] env` as needed:

- `WEVAL_START_APP = "1"` when the Task has an application: the verifier
  starts `main:app` from `/app` and passes its URL to `snapshot()`.
- `WEVAL_KEEP_STACK = "1"` when the agent's running stack is itself under
  test, as in the brownfield Task.

An environment that starts an application before the agent runs writes its
process ID to `/tmp/application.pid`, as the shared instructions tell the agent.

`snapshot.py` should capture every fact a check needs: Weaviate schema and
objects (read over REST, with vector presence flags), responses to fixed HTTP
probes, and relevant submitted files. Outcome facts must come from the live
stack because nothing can reconstruct them after teardown. `check.py` reads
only the snapshot, so `weval check` can re-score retained Trials offline.

A check function passes by returning (optionally a note string) and fails by
raising `AssertionError`. Its name, with underscores replaced by dashes, is
the check ID. Its docstring is the description. Its failure message names the
constraint checked and what was observed instead. Reward is 1 only when every
`REQUIRED` check passes; `PREFERRED` checks are reported but do not affect it.

### Task requirements and verification recipes

Prompts and starter/workspace contracts state required capabilities and
Task-specific constraints.

- Use ordinary domain terms without re-explaining conventional behavior, unless
  a Task-specific ambiguity needs resolution.
- Specify an implementation mechanism only when it is an intentional Task
  constraint, not because the verifier uses it.
- Keep probe inputs, sampling rules, comparison procedures, and assertion logic
  in `snapshot.py` and `check.py`.
- Keep every scored behavior and constraint discoverable in the prompt or a
  referenced agent-visible contract, unless the check intentionally detects
  agent behavior.

For example, require pagination through `/search`; keep the larger-request
versus aggregated-pages comparison in `check.py`.

Detection checks leave a constraint unstated because the evaluation question
is whether the agent applies current practice unprompted; stating it would
convert the measurement into instruction-following. They must still name the
constraint in the check description and failure message, and the workspace
should make current practice the natural path through pinned server and client
versions, starter code, or supporting-stack defaults. The greenfield Task's
`weaviate-managed-vectorization` check is one: the prompt says only "local
vectorizer", while the check requires a named vector from `text2vec-ollama` or
`text2vec-transformers` because collection-level vectorizers are the legacy
path in current Weaviate.

### Calibration

Before running agents on a new Task:

1. Run the Oracle and confirm every check passes.
2. Save its snapshot under `tests/fixtures/` and add broken variants in a test:
   change the snapshot the way a plausible wrong solution would (legacy
   vectorizer, missing object, wrong tokenization, wrong default page size)
   and confirm only the targeted check fails, for the stated reason.

## Running and reading Trials

```sh
uv run --env-file .env weval run tasks/<task> --agent <name> [-n 3]
uv run weval check experiment-outputs/<run>/job/<trial>   # re-score offline
```

Real runs cost money (Modal, OpenRouter). Each Trial directory is Harbor's own
output plus `weval.json`. Start there:

- `weval.json`: status (`passed`, `failed`, `incomplete`, `non-result`), the
  Agent, missing logs, and per-check results.
- `verifier/snapshot.json`, `checks.json`, `test-stdout.txt`,
  `application.log`, `docker-compose.log`.
- `agent/`: the harness transcript and stdout. Pi writes
  `pi/sessions/*.jsonl` and `pi.txt`, plus the web-access lockfile, search
  config, and provenance.
- `artifacts/submission/`: the agent's final `/app`.
- `result.json`, `config.json`, `trial.log`: Harbor's record, including the
  harness version and timings.

Never edit or summarise retained logs in place. Write analysis to separate
files. `incomplete` means an expected log is missing; do not treat it as a
scored result.

## Code style

- Type hints. Docstrings state guarantees and failure behavior; they do not
  narrate steps.
- Keep each check's ID, description, and logic together in one function.
- A leading underscore means a private helper, nothing more. All code is
  human-reviewed.
- Files marked vendored (such as `harnesses/pi_web_access/`) are not
  hand-edited.

Test check logic and transcript parsing against real retained runs.

## Pre-0.1 formats

While the project version in `pyproject.toml` is below `0.1.0`:

- revise formats (snapshots, `weval.json`, `agents.toml`) in place;
- use schema version `"1"` when a schema becomes necessary;
- treat schema migrations and version increments as approval-required changes.

## Commits

Tag the subject with authorship: `[AGENT]`, `[HUMAN]`, `[AGENT+HUMAN]`, or
`[HUMAN+AGENT]` (primary author first).
