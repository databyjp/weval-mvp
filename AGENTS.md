# weval development

weval runs Weaviate coding Tasks against agent harnesses and keeps what is
needed to analyse each Trial. Most work here should be writing Tasks and
reading results, not growing the framework. Use [`GLOSSARY.md`](GLOSSARY.md)
as the domain language.

## General

If subagents are available, use them to run tests or searches unless there is a specific reason not to.

## Layout

- `tasks/<stage>/<scenario>/`: one Task each (see below).
- `agents.toml`: named Agents (harness, version, model).
- `src/weval/run.py`: builds the Harbor package, runs it on Modal, writes `weval.json`.
- `src/weval/verify.py`: shared verifier that runs inside the Trial environment.
- `src/weval/shared-instructions.md`: Trial-environment notes appended to every
  Task's prompt when it is packaged.
- `src/weval/shared-compose.yaml`: Compose overlay applied to every Trial
  environment: the Trial network, `WEAVIATE_*` settings, and Docker socket.
- `src/weval/harnesses/<harness>.py`: Harbor agent config, expected logs, and
  any harness-specific setup (for example, Pi's pinned `pi-web-access`).
- `experiment-outputs/`: retained Experiment runs (git-ignored).

## Coding style & abstractions

Code quality and long-term maintainability is very important.

While code "quality" is a nebulous concept, think principles laid out
in classic software engineering practices; especially those in
"Philosophy of Software Design" and "How to Effectively Maintain Legacy Code".

The easier a human maintainer finds it to read and understand the code,
the more likely they will be to provide helpful inputs.

Additional guidelines:

- Prefer to keep the framework small where there is a choice.
- The framework is very likely to end up with dozens of Tasks. Add a shared abstraction where proven to be needed (e.g. three+ Tasks) or if it is anticipated to be useful.
- If a change
makes the framework noticeably larger, ask first.

## Failed checks are extremely useful findings

weval exists to find where agents fall short, and then to help improve them.

So a failed check on an agent Trial is a very useful result that identifies an opportunity.
You must not treat a failed check as a defect to remove.

Do not be afraid to allow tasks to include vagueness or under-specification simulating a user.
Similarly, such a task is useful to sample likely agent responses,
and design helpful resources and treatments.

Classify each failure before acting on it:

- agent gap: the agent missed something it could have discovered;
- Weaviate gap: the product or its docs led the agent astray;
- scorer bug: `snapshot.py` or `check.py` misjudged a correct solution;
- Task defect: the prompt or workspace hid or contradicted a scored
  constraint.

Only scorer bugs and Task defects call for a weval change. Do not loosen a
check, reword a prompt, or demote a check to make agent Trials pass. Do not
add checks to manufacture failures either: every check must test something
the Task's question needs, and the Oracle must pass it.

## Task Definition

A Task lives at `tasks/<stage>/<scenario>/`. The stage is the kind of job:

- `build`: write new application code;
- `deploy`: stand up or change running infrastructure;
- `resolve`: fix a reported fault on a running system;
- `investigate`: answer a question by research, without changing a system.

The scenario names the use case in a few words, such as `sku-search`. Add a
stage when a Task needs one, and add it to `STAGES` in `tests/test_verify.py`.

A Task is a directory that runs without framework changes:

| File | Purpose |
|---|---|
| `instruction.md` | What the agent is told (Harbor's file name for the prompt). Packaging appends `src/weval/shared-instructions.md`. |
| `prompts/<prompt-variant>.md` | Optional prompt variants, used instead of `instruction.md` with `weval run --prompt-variant <prompt-variant>`. `check.py` then lists each prompt variant's own checks ([reference](docs/reference.md#prompt-variants)). |
| `task.toml` | Harbor task config: timeouts, `/app` artifact, healthcheck, verifier env. |
| `environment/` | Harbor environment: `Dockerfile`, starter app, fixtures, and an optional Compose overlay for Task-specific settings such as a healthcheck. |
| `solution/solve.sh` | The Oracle solution. It must pass every check. |
| `snapshot.py` | `snapshot(app_url) -> dict`: dump the live state to JSON. `app_url` is `None` without an app. |
| `check.py` | `REQUIRED` and `PREFERRED` lists of check functions over the snapshot. |

Each Task also has a page at `docs/tasks/<stage>/<scenario>.md`
([how to define a Task](docs/how-to/define-a-task.md#task-page)).

`verify.py` starts the submitted Compose stack, calls `snapshot()`, and scores
the result. Set these in `[verifier] env` as needed:

- `WEVAL_START_APP = "1"` when the Task has an application: the verifier
  starts `main:app` from `/app` and passes its URL to `snapshot()`.
- `WEVAL_KEEP_STACK = "1"` when the agent's running stack is itself under
  test, as in `deploy/document-search-upgrade`.

An environment that starts an application before the agent runs writes its
process ID to `/tmp/application.pid`, as the shared instructions tell the agent.

`snapshot.py` should capture every fact a check needs: Weaviate collection definition and
objects (read over REST, with vector presence flags), responses to fixed HTTP
probes, and relevant submitted files. Outcome facts must come from the live
stack because nothing can reconstruct them after teardown. `check.py` reads
only the snapshot, so `weval check` can re-score retained compatible Trials offline.

A check function passes by returning (optionally a note string) and fails by
raising `AssertionError`. Its name, with underscores replaced by dashes, is
the check ID. Its docstring is the description. Its failure message names the
constraint checked and what was observed instead. Reward is 1 only when every
`REQUIRED` check passes; `PREFERRED` checks are reported but do not affect it.
When the snapshot fails, the verifier scores `{"error": <traceback>}`, so
every check must fail on it: read snapshot keys directly rather than with
defaults that could pass. `tests/test_verify.py` enforces this for every Task.

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
versions, starter code, or supporting-stack defaults. `build/ecommerce-search`'s
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
uv run --env-file .env weval run tasks/<stage>/<scenario> --agent <name> [-n 3] [--local] [--prompt-variant <prompt-variant>]
uv run weval check experiment-outputs/<run>/job/<trial>   # re-score offline
```

Real runs cost money (Modal, OpenRouter). This is not a problem, but confirm with the user.

Each Trial directory is Harbor's own output plus `weval.json`. Start there:

- `weval.json`: status (`passed`, `failed`, `incomplete`, `non-result`), the
  Agent, the prompt variant, missing logs, per-check results, and `usage` (tokens, cost, tool
  calls, URLs, and search queries).
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

## Pre-0.1 formats

While the project version in `pyproject.toml` is below `0.1.0`, treat almost all parts of this project as mutable.

For example:
- revise formats (snapshots, `weval.json`, `agents.toml`) in place;
- use schema version `"1"` when a schema becomes necessary;
- treat schema migrations and version increments as approval-required changes.

## Commits

Tag the subject with authorship: `[AGENT]`, `[HUMAN]`, `[AGENT+HUMAN]`, or
`[HUMAN+AGENT]` (primary author first).
