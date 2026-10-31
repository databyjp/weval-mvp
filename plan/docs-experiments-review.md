# Review: the Markdown docs experiments

An independent review of the HTML against Markdown experiments in
`plan/docs-improvements.md` and the export variants that followed (iter1,
iter2, iter3). I recomputed every figure here from the retained transcripts
rather than from `weval.json` or the previous agent's scripts. Section
[Method](#method) lists what I computed and where the scripts are.

## Decisions

### Deploy: ship iter1 now

Ship the iter1 export. More Trials would not change this decision.

Evidence:

- On the five fixed pages, iter1 serves the same text as docs.weaviate.io.
  I compared OpenCode's fetches of both: the only differences are the HTML
  page footer ("Additional resources", "Need help?", "Questions and
  feedback") and line breaks inside code blocks.
- What the model carries is smaller, and the size depends on the page, not
  the run. OpenCode's context on the turn after the five reads fell 18–19%
  for all four models (Sonnet 67.7k to 55.3k tokens, DeepSeek 44.6k to
  36.5k, GLM 43.2k to 35.1k, GPT 41.2k to 33.2k), varying under 0.5%
  between Trials of an arm. Claude Code's `WebFetch` summarizer input fell
  21% (41.6k to 33.0k tokens for Sonnet).
- I found no regression in answers. All 109 graded fixed-page Trials (87
  three-language, 22 Python) recommended HNSW, 8-bit RQ, and server-side
  batching for Python and TypeScript, in both arms.
- Go answers were at least as good on iter1. In the one batch that ran both
  arms (2026-10-29, "use only" prompt), 11 of 14 iter1 Go import answers
  used v6 `collection.Batch`, against 6 of 14 HTML. Section
  [What the log missed](#what-the-log-missed) gives the mechanism.
- The deploy is additive and reversible. HTML pages don't change, and
  removing the export and edge function reverts it.

Know before shipping:

- Shipping changes what Claude Code users get by default, not only agents
  that ask for `.md`. The draft's edge function answers Claude Code's
  `Accept: text/markdown, text/html, */*` with Markdown at the normal URL. I
  confirmed it on the iter1 draft: `/weaviate/manage-objects/import` returns
  `text/markdown`, 32,456 bytes. The same URL on docs.weaviate.io returns
  427,922 bytes of HTML. The Claude Code Markdown arm in these runs is
  therefore what users will get, which strengthens the evidence above.
- Harnesses whose HTML extraction keeps only the default tab will read
  more. Pi's `fetch_content` returned 82,410 characters for the five HTML
  pages and 116,571 for the Markdown ones (41% more), because its HTML
  extraction drops every tab but Python. That reader gains the TypeScript
  and Go code it had no way to see.
- B2's shortened vectors are untested by any Trial: none of the five pages
  has a long vector literal.

Would change it: a larger same-batch run in which iter1's answers are worse
than HTML's on any scored item, or a Go v6 rate on HTML that matches or
exceeds iter1's.

### iter3 (Go v6 before v5, "Go (v5, legacy)"): optional, no agent benefit shown

At two Trials per arm and three Agents, iter3 produced the same Go import
answers as iter1 in the same batch: 2 of 6 v6 against 2 of 5. That rules out
a large effect only. The relabel also changes the HTML label that people
see, so treat it as a docs-team decision on its own merits. Don't claim it
helps agents.

Merge weaviate/docs#587 (C6) first. In the "use only" batches, 26 graded
Go import answers used v5 or client-side code. All 15 from Agents other than
GPT state that the Go client lacks server-side batching, the concepts page's
claim; two of them say it of v5 only. OpenCode GPT 6.1 Terra wrote v5 in all
11 of its graded Trials, across every arm. In 9 of them it named the
conflict between the two pages and chose "the documented Go v5" client.

### Blog: yes, scoped to mechanisms and per-page measurements

The results support a post about how agent harnesses read docs and what
that means for a Markdown export. They don't yet support a post claiming
that Markdown makes agents cheaper or more accurate overall. The claim
table is in [Blog claims](#blog-claims).

## Claims in the log, checked

| # | Claim | Verdict |
|---|---|---|
| 1 | Markdown cut what the harness read by about a fifth | True for OpenCode and Claude Code's summarizer. False for Pi, which the log left out. |
| 2 | Total input follows turn count more than page size | True |
| 3 | Claude Code's format effect shows in the summarizer input | True. Also, the summary decides the Go answer. |
| 4 | iter2 raised input 40–70% for most Agents; saved 5–7% on Python only | Numbers right. Mechanism is an extra turn. Prompt confound unresolved. 5–7% holds only for Claude Code Sonnet and Haiku. |
| 5 | Content over format for Go answers | Holds between Markdown builds. Between HTML and Markdown, format also moved the Go answers. |
| 6 | Open-ended Tasks too noisy; fixed pages made format measurable | True |

### 1. Size

OpenCode's `webfetch` returned 146,886 characters for the five HTML pages
and 116,097 for iter1 in every graded Trial on 2026-10-29 (146,879 on
2026-10-30). The log's ranges (146,910–147,019; 116,121–116,154) differ by
about 25 characters, which I attribute to counting. The context after the
reads (figures above) is the better measure, because it is in each model's
own tokens.

Claude Code's summarizer input was 41.6–41.8k tokens on HTML and
33.0–33.2k on iter1, for both Sonnet and Haiku Agents.

The log drops the Pi Trials from the first batch "since OpenCode replaces
Pi". Those Trials are the counterexample: Pi read 41% more on Markdown
(figures above). "Markdown reads smaller" holds only for a harness that
converts every tab of the HTML. Any published version of claim 1 has to name
the harness.

### 2. Turns

Within each OpenCode Agent and arm, context per turn is nearly fixed and
turn count varies 2–3 times, so turns decide total input. OpenCode DeepSeek
on iter1, five Trials across three days, took 3, 3, 5, 6, and 7 turns for
86k to 287k total input, with the context after reads at 36.5–36.7k every
time. At equal turn counts, iter1's total was 10–15% lower: DeepSeek at 5
turns, 162k and 165k on HTML against 141k and 142k on iter1; GLM at 6 turns,
216k against 200k.

One possible format effect on turns is unexplained. OpenCode GPT 6.1 Terra
took 6–9 turns in all 5 iter1 Trials (4 of them with `todowrite` planning
calls) against 3–4 in both HTML Trials. The prompts differ only in their
URLs. Two HTML Trials can't separate this from chance.

### 3. Claude Code

The main model sees `WebFetch` summaries, so its input barely changes:
Sonnet's main-model input was 79–80k on HTML and 81–86k on iter1, slightly
higher because the Markdown summaries were longer (8.3–8.9k characters
against 11.2–15.4k).

The summary matters for correctness more than for tokens. For Claude Code
Sonnet, the Go import answer matched the import-page summary in 14 of 14
Trials: v6 code when the summary contained `collection.Batch`, v5 or
client-side code when it didn't. The summary contained the v6 example in 1
of 3 HTML Trials and 5 of 7 iter1 Trials. On HTML, the summaries returned
"## Go (v5): Manual Batching" or quoted "The Go client does not support
server-side batching". On iter1 they returned "## Go (v6)" with
`collection.Batch(ctx, ...)`.

### 4. iter2

The figures match the transcripts. "Most" means 4 of the 6 Agents with an
iter1 comparison: Claude Code Haiku +46%, Claude Code Sonnet +48%, OpenCode
Sonnet +41%, OpenCode GPT +57%. Claude Code Opus rose 4%. OpenCode DeepSeek
fell 33%, but against a single iter1 Trial (287k), and DeepSeek's iter1 range
across days is 86–287k.

The cost comes from an extra round trip, not from reading more. OpenCode
read only 8% more characters on iter2 (125,610 against 116,097), but the code
pages can only be fetched after the landing pages reveal their links. OpenCode
Sonnet took 4 turns against 3, with similar context per turn.

The prompt confound stands: the iter2 prompt adds "and the code example
pages they link to". Every OpenCode Trial fetched all six code pages,
including two Python pages that repeat the landing page. Since iter2 isn't
proposed for shipping, I wouldn't spend a run on it. Drop or hedge the
finding in the blog.

On the Python Task, the 5–7% saving holds for Claude Code Sonnet (119k, 110k,
102.5k for HTML, iter1, iter2) and Haiku (175k, 171k, 162k), with Trials of
an arm within 3k of each other. All of it is summarizer input (41.6k, 33.0k,
25.2k). OpenCode Sonnet (105–186k) and Claude Code Opus (110–535k) vary too
much to say. The log's conclusion states this correctly ("where the Trials
are consistent").

### 5. Content and format in the Go answers

I agree with the log between Markdown builds. iter1 and iter3 Go answers
didn't differ. The remaining v5 answers cite the concepts page, and GPT
picks v5 deliberately.

Between HTML and Markdown, format also moved the answers. The log's own
note from batch 1, "the harness's page extraction may decide which page
wins", was close, but the log didn't follow it up. Section
[What the log missed](#what-the-log-missed) has the evidence.

### 6. Method

Confirmed. On the open-ended Tasks, Trials of the same Agent and arm took 7
to 39 turns. Re-scored offline with the current checks (`weval.rescore`),
nearly every open-ended Trial passes in both arms, so those checks can't
separate formats either. The four failures are `weaviate-version-latest`:
each answer copied v1.40.0 from the release notes' hand-written "Latest
patch" table (C1). That is a Weaviate gap, and it appears in both arms.

## What the log missed

HTML-to-text conversion loses the code tab labels, and on the import page
that makes the Go v5 caveat read as if it applied to all Go.

OpenCode's conversion of the HTML import page puts every tab label on one
line, then prints the panels without labels and with their line breaks
removed:

```
PythonJavaScript/TypeScriptGo (v5)Go (v6)JavaC#
...
This client does not support server-side batching. Use [manual batching](#manual-batching) instead.
```

The Markdown export labels each panel:

```
**Go (v5)**

This client does not support server-side batching. Use [manual batching](...) instead.

**Go (v6)**
```

In the HTML, the unlabelled v5 sentence sits directly before the v6 code,
and the concepts page says the same thing of "the Go client". Claude Code's
summarizer made that reading in both "use only" HTML Sonnet Trials (claim
3). Pi's extraction drops the Go panels entirely, so Pi's Go code came from
the model's training: v5 or REST in all 5 HTML Trials.

Go import answers that use v6 `collection.Batch`, "use only" prompt, Pi
excluded (it wasn't run with that prompt):

| Arm | Same batch as HTML (2026-10-29) | All batches |
|---|---|---|
| HTML | 6 of 14 | 6 of 14 |
| iter1 | 11 of 14 | 22 of 30 |
| iter1, without GPT 6.1 Terra | 11 of 12 | 22 of 25 |
| HTML, without GPT 6.1 Terra | 6 of 12 | 6 of 12 |

Fisher's exact test gives p = 0.12 for 11/14 against 6/14 and p = 0.07
without GPT. That is suggestive, not established. The first batch, run
without the "use only" prompt and one Trial per arm, went the other way (5
of 7 HTML, 4 of 7 iter1). In that batch Claude Code Haiku downloaded the Go
v6 module and GPT installed clients, so the answers didn't come from the
pages alone.

I classified answers by regex over `findings.json`, then read every
ambiguous one: answers that showed both APIs, a v5 import path with a v6
call, or client-side code without an API. Where an answer recommends v6
and gives v5 as a fallback, I counted v6.

## Non-passing Trials

Every non-passing fixed-page Trial is an infrastructure failure. None is an
agent gap, scorer bug, or Task defect.

| Trial | Recorded | Cause, from logs |
|---|---|---|
| RRGsCEr (OpenCode DeepSeek, HTML) | `timed-out`, `ApiRateLimitError` | exit 137 (OOM kill) after 2 turns |
| tNyca9b (OpenCode DeepSeek, iter1) | `timed-out`, `NonZeroAgentExitCodeError` | OpenRouter 402, `in_flight_budget_exhausted` |
| rSiw8SC (OpenCode Sonnet, iter2) | `timed-out`, reward 1.0 | 402 after it wrote `findings.json`; tokens match its twin (184,157 against 184,190) |
| NfBAJUr, nx5CT6f, n9PApGq | `non-result` | `apt-get` network errors in setup |
| 21 Python-Task Trials | `non-result` | setup network errors and 360 s setup timeouts |

The log excludes rSiw8SC. Including it changes nothing. For the 402s,
Harbor's exception type is wrong, and weval turns it into `timed-out`
rather than `non-result`. That is a weval follow-up, separate from this
review.

OpenCode reports zero cost for every step of 9 GPT 6.1 Terra Trials,
baseline as well as Treatment arms and on all three Tasks, so the cause isn't
format. Treat OpenCode GPT cost as missing, and compute it from tokens if
needed.

## Blog claims

Safe as they stand (deterministic, or visible in every Trial):

- Harnesses convert HTML differently, so a page's format affects agents
  through the harness. OpenCode keeps every code tab but drops their labels
  and line breaks. Pi keeps only the default tab. Claude Code hands the page
  to a summarizer model with a prompt the main model writes. Name the
  harness versions (OpenCode 1.19.4; see each Trial's `weval.json`).
- On five fixed pages, Markdown cut the context an OpenCode agent carries
  per turn by 18–19% for four models, and Claude Code's summarizer input by
  21%. For a harness that keeps only the default HTML tab, Markdown is
  larger (41% on these pages) and carries the other languages' code.
- Total tokens per task depend on turn count, which varied 2–3 times between
  identical Trials, more than on a 20% change in page size. At two Trials
  per arm, total input and cost can't show a page-format effect.
- A contradictory docs sentence propagates into code. All 15 non-GPT v5 or
  client-side Go answers repeat the claim of the concepts page's "The Go
  client does not yet support them". GPT 6.1 Terra chose v5 in all 11 of its
  "use only" Trials and named the conflict in 9.
- Open-ended research Tasks were too noisy to measure format. Fixing the
  pages made it measurable. Present this as method.

Safe with hedging:

- For Claude Code, the summary decides the answer: in 14 of 14 Sonnet
  Trials the Go code followed what the summary kept. Say "in our Trials,
  one Agent".
- Splitting code into per-language pages cost multi-language readers more,
  because finding the pages takes another round trip. Hedge: two Trials per
  arm, and a prompt change that may have invited fetching every code page.
- Reordering Go tabs and labelling v5 "legacy" didn't change the answers
  while the contradictory sentence remained. Hedge: two Trials per arm,
  three Agents.

Need more runs first:

- "Markdown makes agents pick the right Go client" (11/14 against 6/14,
  p = 0.12). Run A below answers it.
- Any percentage saving in total tokens or cost. The current data can't
  support one, and the absolute amounts are small (Claude Code Sonnet on
  the Python Task: $0.124 per Trial on HTML, $0.110 on iter1).
- Any claim about "agents" in general. Seven Agents, two harnesses after
  Pi was dropped, one fixed-page Task family.

## Proposed runs

Run A answers the open quality question. Don't start it without your
confirmation. Run it before weaviate/docs#587 reaches docs.weaviate.io:
after that, the HTML baseline loses the contradictory sentence and iter1
keeps it. If #587 merges first, rebuild iter1 on top of it.

| Run | Task | Agents | Treatments | Trials per arm | Question |
|---|---|---|---|---|---|
| A | `investigate/index-import-pages` | `claude-code-sonnet-5.5`, `opencode-claude-sonnet-5.5`, `opencode-deepseek-v4.1-flash-1017`, `opencode-glm-5.3-flash` | baseline, `markdown-docs-iter1` | 5 | Does Markdown raise the share of v6 `collection.Batch` Go answers? |
| A+ (optional) | same | `opencode-gpt-6.1-terra` | baseline, `markdown-docs-iter1` | 5 | Does GPT take more turns on Markdown (6–9 against 3–4)? |

Run A's Agents are the ones whose Go answers varied. Claude Code Haiku and
Opus wrote v6 in every "use only" Trial, and GPT never did, so they add no
information about the Go rate. Five Trials per arm departs from the
one-Trial default because a rate needs several Trials. Pooled over four
Agents, it gives 20 per arm, enough to tell 45% from 80% most of the time.

Rough cost, from the per-Trial costs in these runs, all `--local` (no
Modal):

| Agent | Per Trial | Run A (10 Trials) |
|---|---|---|
| `claude-code-sonnet-5.5` | about $0.15 | $1.50 |
| `opencode-claude-sonnet-5.5` | $0.14–0.30 | about $2.50 |
| `opencode-deepseek-v4.1-flash-1017` | about $0.015 | $0.15 |
| `opencode-glm-5.3-flash` | about $0.01 | $0.10 |
| `opencode-gpt-6.1-terra` (A+) | $0.08–0.10 where reported | about $1 |

Run A is about $4.50 and A+ about $1, at OpenRouter rates. Run each Agent's
two arms together, about three arms at a time, so arms stay in the same
batch.

I don't recommend a run for the iter2 prompt confound or for iter3. Neither
build is proposed for shipping, and the blog can drop or hedge those
findings.

## Method

Scripts, in
`/private/tmp/claude-501/-Users-jphwang-code-wip-weval/b5839235-6beb-4515-a844-da7c7e085594/scratchpad/review/`
(session scratchpad; copy them if you want to keep them):

- `inventory.py`: every investigate Trial from 2026-10-29 on, from
  `weval.json` and `result.json`;
- `extract.py`: per Trial, from the transcripts, turns, total input (input,
  cache reads and cache writes, as `token_usage` counts them), Claude Code's
  main-model and summarizer input split by model, characters returned by
  fetch tools, `curl` output, and fetched URLs;
- `answers.py`: regex classification of each `findings.json` (index,
  compression, import method, Go client), which I checked by reading every
  ambiguous answer;
- `rescore_all.py`: offline re-scoring of the open-ended Trials with
  `weval.rescore` (writes nothing to the Trial directories).

The OpenCode context after the reads is the input of the first request after
the request that issued the last `webfetch`. I didn't use the previous
agent's `fetched3.py` or `fetched-py.py`. My figures agree with the log's
except for the small character-count offsets noted under claim 1.
