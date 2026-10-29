# Reference

## task.toml

`tasks/<stage>/<scenario>/task.toml` is the Harbor task config for one Task. Harbor
reads it directly; weval passes it through unchanged at packaging.

| Key | Function (Harbor-defined) |
|---|---|
| `artifacts = [{ source, destination }]` | After the Trial, copy the container path `source` into the Trial directory as `artifacts/<destination>/`. e.g.: `artifacts = [{ source = "/app", destination = "submission" }]` copies the agent's final `/app` as `artifacts/submission/`; without this line the agent's work would be lost at teardown. |
| `[agent] timeout_sec` | Wall-clock budget for the harness run. |
| `[verifier] timeout_sec` | Wall-clock budget for the verifier: stack preparation, `snapshot()`, and checks. |
| `[verifier] env` | Environment variables for the verifier process. weval reads `WEVAL_START_APP` and `WEVAL_KEEP_STACK` from here (below). |
| `[environment] build_timeout_sec` | Budget for building the environment images. |
| `[environment.healthcheck]` | `command` is retried every `interval_sec` inside the environment; the agent starts only after it succeeds. `start_period_sec` is the grace period for slow setup such as seeding. |

weval reads its own Task settings from `[metadata]`, which Harbor's schema
leaves free-form:

| Key | Function (weval-defined) |
|---|---|
| `draft = true` | The Task is not run for now. `weval run` refuses it unless you pass `--draft`; its tests still run. |
| `motivation = "..."` | The Task's question, in place of a Task page ([how to define a Task](how-to/define-a-task.md#task-page)). Every check then needs a docstring. |
| `weaviate_workspace = false` | Leaves out the Weaviate settings ([Trial environment](#trial-environment)). |

### Verifier flags

Set in `[verifier] env` per Task; a Task sets neither, either, or both.

- `WEVAL_START_APP = "1"`: the Task has an application. The verifier starts
  `main:app` from `/app` and passes its base URL to `snapshot()`. Without
  the flag, `snapshot()` receives `None`. The start recipe is fixed:
  uvicorn serves `main:app` on port 18000, and the verifier waits up to
  120 s for `/openapi.json` to answer 2xx. FastAPI serves that route by
  default; another ASGI application must serve it too. A Task whose
  application does not fit can start it from `environment/` instead and
  probe fixed URLs in `snapshot.py`.
- `WEVAL_KEEP_STACK = "1"`: the agent's running stack is itself under test,
  for example because its Weaviate volume holds the data being scored. The
  verifier skips `docker compose up` and scores whatever the agent left
  running.

Without `WEVAL_KEEP_STACK`, the verifier runs `docker compose up --wait` on
the submitted `/app/docker-compose.yaml`. Compose leaves running containers
with unchanged configuration in place, so the verifier also scores the agent's
stack and data whenever the agent left them running. The stack is fresh only
when the agent stopped it. Either way, the verifier saves the Compose logs and
then runs `docker compose down --volumes`.

When the submitted `/app` has no `docker-compose.yaml`, the verifier skips
Compose entirely and writes no `docker-compose.log`. That is normal for a Task
with no stack. In a Task where the agent should have written the file, the
Trial fails at the snapshot, typically because Weaviate is unreachable.

An environment that starts an application before the agent runs writes its
process ID to `/tmp/application.pid`. The shared instructions tell the agent
this is how to find and restart it.

## Treatments

A Treatment is a directory `treatments/<treatment>/` with a `README.md`
stating the experimental question, which is not given to the Agent, and at
least one of:

- `skills/`: one subdirectory per skill, each with a `SKILL.md`. Harbor
  installs them where the harness looks for them:
  `$CLAUDE_CONFIG_DIR/skills/` for Claude Code and `~/.agents/skills/` for
  Pi. They are not in `/app`, so they are not in `artifacts/submission/`.
- `prompts/<stage>/<scenario>.md`: a prompt that replaces that Task's
  `instruction.md`. The shared instructions follow it as usual. A Treatment
  with `prompts/` runs only on the Tasks it has a prompt for, and every Agent
  reads the prompt, whereas a harness loads a skill only when it chooses to.

`weval run --treatment <treatment>` copies the directory to the run
directory's `treatment/`, records the name in each Trial's `weval.json` as
`treatment`, and adds `+<treatment>` to the run directory's Agent part. A
Treatment that is unknown, has neither part, or has prompts but none for the
Task fails before anything runs. Without `--treatment`, a Trial is a baseline
and `treatment` is `null`.

## Trial environment

Every Trial environment's `main` service, where the agent works, gets these
settings from `src/weval/shared-compose.yaml`:

| Setting | Value |
|---|---|
| `COMPOSE_PROJECT_NAME` | `<Harbor project>_submission`, so the agent's stack is a separate Compose project. |
| `TRIAL_NETWORK` | `<Harbor project>_default`, the network the agent's stack must join. |
| `/var/run/docker.sock` | The Docker socket, mounted so the agent and verifier can run Compose. |

It also gets these from `src/weval/weaviate-compose.yaml`, unless the Task's
`task.toml` sets `[metadata] weaviate_workspace = false`. A Task opts out when
its workspace must not suggest a data store, as in
`investigate/db-recommendation`.

| Setting | Value |
|---|---|
| `WEAVIATE_HTTP_HOST`, `WEAVIATE_HTTP_PORT` | `weaviate`, `8080` |
| `WEAVIATE_GRPC_HOST`, `WEAVIATE_GRPC_PORT` | `weaviate`, `50051` |

`weval` passes these files to Harbor as extra Compose overlays
(`extra_docker_compose`); Harbor applies them after the Task's own overlay.

Claude Code Agents are installed from a binary that the host downloads once per
version and platform, checks against the release manifest's SHA-256, and keeps
gzipped (about 110 MB each) in `~/.cache/weval/claude-code/`, or under
`$XDG_CACHE_HOME`, so Trials do not download Claude Code themselves. Before
Modal Trials start, `weval run` uploads the `linux-x64` binary to the Modal
Volume `weval-claude-code` if it lacks that version, and each Trial reads it
from the Volume, mounted read-only at `/opt/weval/claude-code`. A local Trial
uploads the binary from the host cache instead. Concurrent `weval run`
processes on one host wait on a lock file in the version's cache directory,
so only one of them downloads or uploads each binary.

A Task's `environment/` supplies the `Dockerfile` and anything specific to that
Task. Its optional `docker-compose.yaml` overlay is applied before weval's, for example to add a healthcheck on `main`.

## The Trial directory

Each retained Trial directory is Harbor's own output plus weval's
`weval.json`. `weval.json` is the entry point for reading a Trial.

| Path | Contents |
|---|---|
| `weval.json` | Status (`passed`, `failed`, `incomplete`, `timed-out`, `non-result`), the Agent, the Treatment, `fingerprints` (below), missing logs, the model error that ended the session (if any), per-check results, and `usage`: the Agent's tokens and cost, tool-call counts, external URLs in tool-call arguments, and search queries. Tokens and cost come from Harbor, except for Claude Code, whose own counts include the requests in which `WebFetch` summarises pages. Claude Code's `cost_usd` is an estimate from the OpenRouter prices in `harnesses/claude_code.py`'s `PRICES`, and `null` for a model missing there. |
| `verifier/` | `snapshot.json`, `checks.json`, `test-stdout.txt`, `application.log`, `docker-compose.log`. |
| `agent/` | The harness transcript and stdout. Pi writes `pi/sessions/*.jsonl` and `pi.txt`, plus the web-access lockfile, search config, and provenance. Claude Code writes `claude-code.txt` (stream JSON) and `sessions/projects/-app/*.jsonl`. Harbor converts both to `trajectory.json`. |
| `artifacts/submission/` | The agent's final `/app`. |
| `result.json`, `config.json`, `trial.log` | Harbor's record, including the harness version and timings. |

`incomplete` means an expected log is missing; it is not a scored result.
`timed-out` means Harbor recorded an agent limit but the verifier still graded
the submission; the reward is recorded and does not count as `passed`.
`non-result` names its cause in `exception`, or in `model_error` when the
agent's session ended because a model request failed after the harness's own
retries, such as a provider rate limit; the verifier may still have graded
that submission, but the Trial does not count. A snapshot error scores `failed`
at any `error_stage`: `stack` and `app` are the agent's submission failing to
start, and `snapshot` is `snapshot.py` raising, usually on a stack the agent
left broken.

`fingerprints` versions what the run's Trials were given. Each value is 12
hex digits of a SHA-256 over file paths and contents:

| Key | Covers | A change means |
|---|---|---|
| `task` | The Task directory without `check.py`, plus `shared-instructions.md`, `verify.py`, and the Compose overlays | the Trials must be re-run |
| `check` | The Task's `check.py` | the Trials can be re-scored with `weval check` |
| `treatment` | What the Treatment gives the Agent on this Task: its `skills/` and its prompt for the Task; `null` for a baseline. Its `README.md` and its prompts for other Tasks are not covered. | a different Treatment version |

Trials recorded before fingerprints existed have `fingerprints` missing or
`null`. The docs site and the latest releases change too and can't be
hashed; the run directory's timestamp dates them.

Retained logs are evidence: write analysis to separate files rather than
editing or summarising a log in place.
