# How to read a Trial

To compare a [Treatment](../reference.md#treatments) with its baseline,
analyse the retained runs once a batch of runs has finished, naming any run
in the comparison:

```sh
uv run --env-file .env weval analyse experiment-outputs/<run>
```

`weval run` does not analyse: a comparison spans every Agent's runs, so each
new run would ask the analyst again.

A comparison holds one Task and prompt variant across Agents: the baseline
runs and the Treatment runs of every Agent that ran both arms. Agents with
runs in one arm only are listed and left out, so both arms cover the same
models. It gives each arm's required pass count, failed checks, and mean
usage per Trial, and for each Agent whether the Treatment helped, hurt, or
left its pass rate unchanged. Each usage row counts the Agents whose usage
went up or down, and gives the change in the mean and the median of each
Agent's own change; when they disagree, a few costly models moved the mean
against most Agents. Uncached input leaves out
prompt-cache reads, which make up most of each Trial's input tokens.
A comparison holds only runs with the same Task and check versions, and one
Treatment version ([fingerprints](../reference.md#the-trial-directory)). Runs
recorded before fingerprints existed are pooled with each other, so after a
`check.py` change, re-score both arms with `weval check` (below).
`weval report` likewise covers only each Task's current version, the Task and
check versions of its newest run; earlier versions and their findings are at
the bottom of the Task's page.

An LLM analyst (`MODEL` in `src/weval/analysis.py`) reads the comparison's
computed facts, never the transcripts: pass counts, each Agent's change,
mean usage, and each failed check's Agent, failure message,
[expected value](define-a-task.md#expected-values), and labels. It answers
with a one-sentence result, failure patterns with their Trials, evidence,
and a proposed [failure class](../../AGENTS.md#failed-checks-are-extremely-useful-findings),
caveats, and open questions. weval rejects an answer that cites a Trial or
check that did not fail, states a number missing from the facts, or leaves a
failed required check out of every pattern. It asks again with the problems,
up to three times, and shows a last rejection as rejected. A hand-coded rule
proposes a class for each failed check from the same facts:

- the expected value was shown to the agent: agent gap;
- it was not, and the labelled source is a Weaviate page: Weaviate gap;
- the snapshot failed (`error_stage` set) or gave no expected value: infrastructure failure;
- otherwise unclassified.

Where the rule and the analyst name different classes for the same failed
check, the disagreement is listed for you to decide. The analysis knows
only the facts, so what a docs page says stays in its open questions.
Analyses are saved in `experiment-outputs/_analysis/` and reused until the
facts, prompt, or model change, such as after a new run joins the comparison.

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

After the check results, `weval check` prints diagnostics from the Trial's logs. They explain results and don't change them:

- under a failed check with an [expected value](define-a-task.md#expected-values), whether the agent was shown that value;
- for a Treatment Trial, whether the skill loaded and which Treatment files a tool call named (a glob such as `*.md` reads files without naming them);
- Weaviate deprecation warnings (`Dep024: ...`) the agent was shown, and those in `verifier/application.log`.

`weval run` and `weval check` also label each failed check, given `OPENROUTER_API_KEY` and `TYPESAFEAI_API_KEY`, in two steps:

1. A step finder (`STEPS_MODEL` in `src/weval/labels.py`) reads the whole trace once and picks, for each failed check, the decision step, where the agent made the choice the check found, and the other steps that bear on it. Step numbers are the transcript's on the Trial's report page, and link there. Finding no relevant steps is a valid answer.
2. TypeSafe's Jev model reads only those steps and answers:
   - `cause`: `no_lookup`, `followed_source`, `ignored_current_practice`, `considered_and_rejected`, `environment_forced`, or `no_trace_evidence` (definitions in `CAUSES`);
   - `answer source`: which source shown in those steps the agent took the failed value or approach from, out of the URLs, searches, and Treatment files they showed, or `own-knowledge`.

Each answer has Jev's confidence from 0 to 1; read a low one (below about 0.5) as "check by hand". A source is credited with every tool result that named it, so a `grep` over several files credits all of them. A page Pi read with `get_search_content` counts for the URL it fetched, and a skill Claude Code loaded counts for its `SKILL.md`. A Trial whose snapshot failed is not labelled. Labels are saved in the run directory's `labels/<trial>.json` and reused until a request changes, such as after a `check.py` change.

## Write a note

To record what you or an agent concluded about a result, write a Markdown file at `experiment-outputs/_report/notes/<task page>/<task version>/<name>.md`. The Task page is the Task page's file name under `_report/tasks/` without `.html`, such as `build-ecommerce-search`; the Task version is the `task` fingerprint in the runs' `weval.json`, such as `35f56f59e981`. Start the note with a header; every field is optional:

```markdown
---
author: claude-code
date: 2026-10-28
check: sku-category-field-tokenization
trials: [task__ZYLBTdY]
---
The agent kept `category` as WORD on purpose, to match multi-word categories.
```

`weval report` shows each note on its Task page, beside the version it belongs to; under the finding for its `check`; and on the page of each Trial it names. The report never changes or deletes a note, but deleting `_report/` deletes the notes with it.
