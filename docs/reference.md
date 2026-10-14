# Reference

## task.toml

`tasks/<name>/task.toml` is the Harbor task config for one Task. Harbor
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
  the flag, `snapshot()` receives `None`. The start recipe is fixed: a
  Python ASGI application exposing `app` in `main.py`. A Task whose
  application does not fit can start it from `environment/` instead and
  probe fixed URLs in `snapshot.py`.
- `WEVAL_KEEP_STACK = "1"`: the agent's running stack is itself under test,
  for example because its Weaviate volume holds the data being scored. The
  verifier scores that stack instead of starting a fresh one from the
  submission.

An environment that starts an application before the agent runs writes its
process ID to `/tmp/application.pid`. The shared instructions tell the agent
this is how to find and restart it.

## The Trial directory

Each retained Trial directory is Harbor's own output plus weval's
`weval.json`. `weval.json` is the entry point for reading a Trial.

| Path | Contents |
|---|---|
| `weval.json` | Status (`passed`, `failed`, `incomplete`, `non-result`), the Agent, missing logs, and per-check results. |
| `verifier/` | `snapshot.json`, `checks.json`, `test-stdout.txt`, `application.log`, `docker-compose.log`. |
| `agent/` | The harness transcript and stdout. Pi writes `pi/sessions/*.jsonl` and `pi.txt`, plus the web-access lockfile, search config, and provenance. |
| `artifacts/submission/` | The agent's final `/app`. |
| `result.json`, `config.json`, `trial.log` | Harbor's record, including the harness version and timings. |

`incomplete` means an expected log is missing; it is not a scored result.
Retained logs are evidence: write analysis to separate files rather than
editing or summarising a log in place.
