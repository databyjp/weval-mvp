# Task runs

Each run involves two processes. `weval` runs on the host device. It packages the Task, starts Harbor, and records the result. `verify.py` runs inside each Trial environment, alongside the agent's workspace.

`weval run` triggers `weval.run.run()`. Each run looks as follows:

- `weval` "packages" a Task: the prompt with the shared instructions appended, plus a `tests/` directory holding the shared verifier (`verify.py`), the Task's `snapshot.py` and `check.py`, and `test.sh`, Harbor's verifier entry point.
- `weval` creates a Harbor `JobConfig` and runs the Job until every Trial finishes.
- In each Trial, Harbor starts the environment, runs the agent, copies the agent's final `/app` to `artifacts/submission/`, and then runs `test.sh`.
- `verify.py` snapshots the live stack and scores the snapshot against the Task's checks.
- `weval` writes `weval.json` for each Trial and redacts credentials from the run directory.

Harbor copies the exact submission before verification to `artifacts/submission/`.

Scoring is done on a snapshot. So `weval check` can re-score a retained Trial even after its environment is gone.

If preparing the stack or taking the snapshot raises, `verify.py` saves the traceback as `snapshot.json` with the failing stage, and every check fails with the note `(snapshot failed; see snapshot.json)`. A broken agent-submitted stack or app (`error_stage` `stack` or `app`) is a `failed` Trial: that is the agent's result. A failure in the verifier's own `snapshot` stage is a `non-result`. A Harbor exception with no graded reward is a `non-result`; with a graded reward it is `timed-out`. A missing expected log or submission makes the Trial `incomplete`.
