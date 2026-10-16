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

## Prompt variants

A Task may keep alternative prompts at `prompts/<prompt-variant>.md`;
`instruction.md` is the `default` prompt variant.
`weval run --prompt-variant <prompt-variant>` packages that prompt as the
Task's `instruction.md`, writes its name to the package's
`tests/prompt_variant`, and adds `@<prompt-variant>` to the run directory's
scenario part. An unknown prompt variant fails before anything runs.

The verifier adds the name to the snapshot as `prompt_variant`, also when the
snapshot failed. `check.py` then defines `PROMPT_VARIANT_REQUIRED` and
`PROMPT_VARIANT_PREFERRED`, mapping `default` and every prompt variant name to
check functions scored after the shared `REQUIRED` and `PREFERRED` lists.
`tests/test_verify.py` fails unless both dicts name exactly `default` and the
files in `prompts/`. A snapshot without `prompt_variant`, retained from before
it was recorded, is scored as `default`.

## Trial environment

Every Trial environment's `main` service, where the agent works, gets these
settings from `src/weval/shared-compose.yaml`:

| Setting | Value |
|---|---|
| `COMPOSE_PROJECT_NAME` | `<Harbor project>_submission`, so the agent's stack is a separate Compose project. |
| `TRIAL_NETWORK` | `<Harbor project>_default`, the network the agent's stack must join. |
| `WEAVIATE_HTTP_HOST`, `WEAVIATE_HTTP_PORT` | `weaviate`, `8080` |
| `WEAVIATE_GRPC_HOST`, `WEAVIATE_GRPC_PORT` | `weaviate`, `50051` |
| `/var/run/docker.sock` | The Docker socket, mounted so the agent and verifier can run Compose. |

`weval` passes this file to Harbor as an extra Compose overlay
(`extra_docker_compose`); Harbor applies it after the Task's own overlay.

A Task's `environment/` supplies the `Dockerfile` and anything specific to that
Task. Its optional `docker-compose.yaml` overlay is applied before the shared
one, for example to add a healthcheck on `main`.

## The Trial directory

Each retained Trial directory is Harbor's own output plus weval's
`weval.json`. `weval.json` is the entry point for reading a Trial.

| Path | Contents |
|---|---|
| `weval.json` | Status (`passed`, `failed`, `incomplete`, `non-result`), the Agent, the prompt variant, missing logs, per-check results, and `usage`: the Agent's tokens and cost, tool-call counts, external URLs in tool-call arguments, and search queries. Tokens and cost come from Harbor, except for Claude Code, whose own counts include the requests in which `WebFetch` summarises pages. Claude Code's `cost_usd` is `null` because it has no price for OpenRouter model names. |
| `verifier/` | `snapshot.json`, `checks.json`, `test-stdout.txt`, `application.log`, `docker-compose.log`. |
| `agent/` | The harness transcript and stdout. Pi writes `pi/sessions/*.jsonl` and `pi.txt`, plus the web-access lockfile, search config, and provenance. Claude Code writes `claude-code.txt` (stream JSON) and `sessions/projects/-app/*.jsonl`. Harbor converts both to `trajectory.json`. |
| `artifacts/submission/` | The agent's final `/app`. |
| `result.json`, `config.json`, `trial.log` | Harbor's record, including the harness version and timings. |

`incomplete` means an expected log is missing; it is not a scored result.
Retained logs are evidence: write analysis to separate files rather than
editing or summarising a log in place.
