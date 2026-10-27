# How to read a Trial

To find a Trial, or compare runs, build the report offline:

```sh
uv run weval report
```

Then view `experiment-outputs/index.html` in a browser.

To compare a [Treatment](../reference.md#treatments) with its baseline, open
the Treatments tab. Each row pair holds one Task, prompt variant, and Agent:
the baseline runs, then the Treatment runs, with required pass rate, failed
checks, and mean usage per Trial. The Tasks tab shows baseline runs only.
A row pair holds only runs with the same Task and check versions, and one
Treatment version; the short [fingerprints](../reference.md#the-trial-directory)
under the Task and Treatment names identify them. Runs recorded before
fingerprints existed are marked unversioned and pooled with each other, so
after a `check.py` change, re-score both arms with `weval check` (below).

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

`weval check` loads the Task's current `check.py` from the Task path recorded in `weval.json`. If the Task has moved since the run, pass `--task tasks/<stage>/<scenario>`. Its first line gives that `check.py`'s fingerprint beside the one the Trial recorded; when they differ, the scores may differ from `weval.json`.
