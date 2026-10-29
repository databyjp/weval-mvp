# Task runs

Each run involves two processes. `weval` runs on the host device. It packages the Task, starts Harbor, and records the result. `verify.py` runs inside each Trial environment, alongside the agent's workspace.

`weval run` triggers `weval.run.run()`. It refuses a [draft](../reference.md#tasktoml) Task before anything runs unless you pass `--draft`. Each run looks as follows:

- `weval` "packages" a Task: the prompt (the Task's `instruction.md`, or the Treatment's `prompts/<stage>/<scenario>.md`) with the shared instructions appended, plus a `tests/` directory holding the shared verifier (`verify.py`), the Task's `snapshot.py` and `check.py`, and `test.sh`, Harbor's verifier entry point.
- `weval` hashes what the Trials are given into `fingerprints` ([reference](../reference.md#the-trial-directory)).
- `weval` creates a Harbor `JobConfig` and runs the Job until every Trial finishes.
- In each Trial, Harbor starts the environment, runs the agent, copies the agent's final `/app` to `artifacts/submission/`, and then runs `test.sh`.
- `verify.py` snapshots the live stack and scores the snapshot against the Task's checks.
- `weval` writes `weval.json` for each Trial and redacts credentials from the run directory.
- `weval` labels each failed check ([labels](../how-to/read-a-trial.md#re-score)) when `OPENROUTER_API_KEY` and `TYPESAFEAI_API_KEY` are set.

Harbor copies the exact submission before verification to `artifacts/submission/`.

Scoring is done on a snapshot. So `weval check` can re-score a retained Trial even after its environment is gone.

If preparing the stack or taking the snapshot raises, `verify.py` saves the traceback as `snapshot.json` with the failing stage, and every check fails with the note `(snapshot failed; see snapshot.json)`. A snapshot error at any `error_stage` (`stack`, `app`, or `snapshot`) is a `failed` Trial, or `timed-out` when the agent hit its time limit; the report counts it in the pass rate but in no check's failure rate. A `snapshot`-stage error usually means the agent left its stack broken; when it is a scorer bug instead, the failure's classification records that. A Harbor exception with no graded reward is a `non-result`; with a graded reward it is `timed-out`. A Trial whose session ended on a failed model request is also a `non-result`, whatever was graded. A missing expected log or submission makes the Trial `incomplete`.
