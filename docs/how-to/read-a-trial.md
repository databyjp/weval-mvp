# How to read a Trial

To find a Trial, or compare runs, build the report offline:

```sh
uv run weval report
```

Then view `experiment-outputs/index.html` in a browser.

To compare a [Treatment](../reference.md#treatments) with its baseline, open
the Treatments tab. Each row pair holds one Task, prompt variant, and Agent:
the baseline runs, then the Treatment runs, with required pass rate, failed
checks, and mean usage per Trial. Each pass rate has its 95% Wilson
interval, and the Treatment row adds Fisher's exact p-value against the
baseline; at 5 Trials per arm, only large differences reach a small
p-value. Uncached input leaves out prompt-cache reads, which make up most
of each Trial's input tokens. The Tasks tab shows baseline runs only.
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

After the check results, `weval check` prints diagnostics from the Trial's logs; the report's Trial page shows the same under its checks table. They explain results and don't change them:

- under a failed check with an [expected value](define-a-task.md#expected-values), whether the agent was shown that value;
- for a Treatment Trial, whether the skill loaded and which Treatment files a tool call named (a glob such as `*.md` reads files without naming them);
- Weaviate deprecation warnings (`Dep024: ...`) the agent was shown, and those in `verifier/application.log`.

`weval run` and `weval check` also label each failed check with TypeSafe's Jev model, given `TYPESAFEAI_API_KEY`:

- `answer source`: which source the agent took the failed value or approach from, out of the URLs, searches, and Treatment files whose results it was shown, or `own-knowledge`;
- `verification`: `verified`, `deferred_to_user`, `not_attempted`, or `guessed`.

Each label has Jev's confidence from 0 to 1; read a low one (below about 0.5) as "check by hand". A source is credited with every tool result that named it, so a `grep` over several files credits all of them. Labels are saved in the run directory's `labels/<trial>.json` and reused until the request changes, such as after a `check.py` change; the report shows saved labels only and never calls Jev.
