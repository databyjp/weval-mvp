# How to read a Trial

To find a Trial, or compare runs, build the report offline:

```sh
uv run weval report
```

Open `experiment-outputs/index.html` in a browser. It reads the Tasks,
`agents.toml`, and retained runs, and does not modify any run directory.
Run the command again after a run or a Task change.

The Tasks tab has one row per Task and prompt variant. Each Agent column
shows that Agent's latest run: how many scored Trials (`passed`, `failed`,
or `timed-out`) passed every required check, and which required checks
failed. Click a result to see its runs. Click *definition* for the Task's
summary, settings, checks (read from `check.py`), and prompts. The Agents
in `agents.toml` are listed below.

The Results tab has one row per run: the Task, prompt variant, Treatment,
Agent, date, environment, and output directory. Required and Preferred
show how many scored Trials passed every check of that kind. Cost, tokens
(input plus output), turns (agent messages in `agent/trajectory.json`),
and agent execution time are means per Trial. Filter by Task, prompt
variant, or Agent; click a header to sort, or the Task or Trial count
to list each Trial. A Trial without `weval.json` shows as `unrecorded`.

Each Trial links to its page under `experiment-outputs/_report/`: the
status, the agent's final message, each check with its notes, usage, the
transcript from `agent/trajectory.json`, and the snapshot as a collapsible
tree. The page links to the retained files it reads.

For one Trial, start at `weval.json` in the Trial directory ([layout reference](../reference.md#the-trial-directory)).

Then follow your question:

- Why did a check fail? See `verifier/checks.json` for the failure message, and
  `verifier/snapshot.json` for the output facts.
- What did the agent do? See `agent/` for the transcript and stdout.
- How many tokens did it use, and what did it look up? See `usage` in
  `weval.json`. A page read from search results without its own fetch is
  not in `usage.urls`.
- What did it submit? See `artifacts/submission/` as the agent's final `/app`.
- Did the infrastructure fail? A `non-result` status records the cause
  in `weval.json`; `result.json`, `trial.log`, and the `verifier/` logs have
  the detail.

`incomplete` means an expected log is missing; do not treat the Trial as a
scored result.

## Re-score

Re-score a retained Trial offline from its snapshot (e.g. after changing the check):

```sh
uv run weval check experiment-outputs/<run>/job/<trial>
```

`weval check` loads the Task's current `check.py` from the Task path recorded in `weval.json`. If the Task has moved since the run, pass `--task tasks/<stage>/<scenario>`.
