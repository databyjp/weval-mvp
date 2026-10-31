# Docs feedback loop: Markdown export

weval measures how agents read the Weaviate docs (`~/code/weaviate/docs`),
we change the staging build, and weval measures again. This file records each
iteration's change, the evidence behind it, and what it did, so the
rationale can be explained to the docs team. The log comes first; the
proposals it draws from follow.

The Tasks are `investigate/docs-token-usage` (versions and recommended
practice) and `investigate/client-code-examples` (the same, with Python,
TypeScript, and Go code). Each iteration runs `claude-code-sonnet-5.5` and
`pi-deepseek-v4.1-flash-1017`, three Trials per arm, locally. Compare total
input (including Claude Code's `WebFetch` summarizer), uncached input, and
cost, not main-model input alone.

## Log

### Iteration 0: HTML against the first Markdown build

- Build: `feat/markdown-export` at f315f8fa, which serves every docs page
  as Markdown at its path plus `.md`
  (`feat-markdown-export--docs-weaviate-io.netlify.app`). Treatment:
  `markdown-docs-staging`.
- Result (notes in
  `experiment-outputs/_report/notes/investigate-*/*/iteration-0.md`):
  - Markdown did not reduce tokens. Claude Code's totals were about equal
    (155k against 161k; 197k against 192k), with half the uncached input and
    a lower cost. DeepSeek used more: 413k against 599k, and 199k against
    248k.
  - Correctness failures came from page content and were the same on both
    arms: a hand-written release table ("4.24.x", "v1.40.0"), no versions on
    the client index, and a quickstart that shows `nearText` as the search.
  - Where the Markdown tokens went: table padding, 1,536-number vectors,
    every language's code, a 68,920-character quickstart, and HTML 404 pages
    for guessed `.md` paths.
- Decision: try the build changes that only delete characters first (B1,
  B2), then the navigation changes (B3–B5), then the content changes
  (C1–C4).

### Iteration 1: unpadded tables and shortened vectors (B1, B2)

- Build: `feat/markdown-export-iter1` at 980bd35a. Treatment:
  `markdown-docs-iter1`, whose prompts differ from `markdown-docs-staging`'s
  only in the host.
- Change: `html-to-markdown.mjs` writes tables with `tablePipeAlign: false`,
  and shortens a bracketed list of 16 or more numbers in a code block to its
  first three values, with a sentence after the block.
- Offline effect, from both converters on the same `build/*.html`: the 393
  docs pages shrink by 10.2% (5,548,480 to 4,983,503 characters).

  | Page | Before | After |
  |---|---|---|
  | `deploy/configuration/env-vars.md` | 132,001 | 49,332 |
  | `weaviate/starter-guides/custom-vectors.md` | 80,881 | 21,965 |
  | `weaviate/search/hybrid.md` | 85,393 | 51,147 |
  | `weaviate/search/similarity.md` | 66,062 | 44,807 |
  | `weaviate/client-libraries/python.md` | 42,830 | 26,549 |
  | `weaviate/release-notes.md` | 28,044 | 12,382 |
  | `weaviate/quickstart.md` | 68,920 | 67,803 |
  | `weaviate/quickstart/local.md` | 61,097 | 60,180 |

- Expectation: lower tokens on docs-token-usage, whose Trials read the
  release notes and the Python client page. Little change on
  client-code-examples, whose Trials mostly read the quickstarts.
- Result (12 Trials, 2026-10-29 17:34, against iteration 0's
  `markdown-docs-staging` Trials, all re-scored with the current checks):

  | Task | Agent | iter0 passed, total input | iter1 passed, total input |
  |---|---|---|---|
  | docs-token-usage | claude-code-sonnet-5.5 | 2/3, 161k | 3/3, 228k |
  | docs-token-usage | pi-deepseek-v4.1-flash-1017 | 3/3, 599k | 3/3, 580k |
  | client-code-examples | claude-code-sonnet-5.5 | 3/3, 192k | 3/3, 197k |
  | client-code-examples | pi-deepseek-v4.1-flash-1017 | 3/3, 248k | 3/3, 912k |

  - The token differences come from how agents read, not from page size.
    Claude Code's iteration-0 median Trial used `WebFetch` (161k); every
    iter1 Trial used `curl`. DeepSeek's iter1 client-code-examples Trials
    read 8–15 pages against 4–6, including `search/hybrid.md` and
    `manage-objects/import.md`, and two of three wrote hybrid search code,
    which no iteration-0 Trial did. The pages that start their reading
    (`weaviate.md`, `quickstart.md`) are unchanged by B1 and B2, so I do
    not attribute the wider reading to them.
  - Agents rarely read a page whole: they slice with `head`, `sed`, and
    `grep`, and Pi's `fetch_content` stops at 30,000 characters. Fetches of
    `release-notes.md` returned 12,236 characters on average in iteration
    0 and 10,924 in iter1, although the page shrank from 28,044 to 12,382.
  - Answer quality, read from each Trial's `findings.json`:
    - docs-token-usage: all six iter1 Trials named both exact versions
      (1.40.3, 4.24.1), against three of six in iteration 0. Iter1 Trials
      fetched `client-libraries/python.md` 12 times against 6.
    - client-code-examples: every answer in every arm used the current
      vector API and Go v6. The two widest-reading DeepSeek Trials gave the
      best answers of all 18 Trials: Go `collection.Batch(ctx, ...)` instead
      of `Data.Insert`, and in vYuaYqH hybrid as the default search in all
      three languages, quoting the docs' "good default".
    - The best answers came from the Trials that used the most tokens
      (912k and 1,243k), so minimizing tokens alone can reward shallow
      reading.
  - Conclusion: B1 and B2 make the export 10% smaller with no change in
    correctness, but at three Trials per arm, run-to-run variation in
    turns, pages read, and tool choice hides an effect of this size.
- Decision: keep B1 and B2. Evaluate build-only changes by page size
  offline. Use Trials for changes meant to alter what agents read or
  answer (B3–B5, C1–C4).
- Learning: one open-ended Task mixes two questions, so split them.
  - Token cost of reading: a Task that names the pages to read and asks
    only questions those pages answer. It fixes the navigation, which caused
    most of the variation here, so a page-format change shows in tokens.
  - Answer quality: the open-ended Tasks, compared between HTML and
    Markdown on the facts each answer should contain, not on tokens.

### Fixed-page reading: index-import-pages (iteration 1 build)

- Task: `investigate/index-import-pages`, which names five pages and
  forbids others. Treatment: `markdown-docs-iter1` against the HTML
  baseline. One Trial per arm, run locally on 2026-10-29. Claude Code and
  OpenCode only. The Pi Trials from the same batch are retained but left
  out, since OpenCode replaces Pi for open harnesses. Token counts for
  OpenCode include cache writes and reasoning (`harnesses/opencode.py`'s
  `token_usage`).
- Result: all 14 Trials passed. Every Trial chose HNSW with 8-bit RQ and
  server-side batching for Python and TypeScript, and none read a sixth
  docs page.

  | Agent | Total input | Uncached input | Cost | Tool calls | Go import |
  |---|---|---|---|---|---|
  | claude-code-haiku-5.5 | 3.30M → 315k | 121k → 73k | $0.118 → $0.086 | 56 → 16 | v6 Batch, v6 Batch |
  | claude-code-opus-5.5 | 682k → 370k | 162k → 66k | $0.828 → $0.625 | 22 → 11 | v6 Batch, v6 Batch |
  | claude-code-sonnet-5.5 | 123k → 113k | 56k → 47k | $0.163 → $0.149 | 8 → 8 | v6 Batch, v5 |
  | opencode-claude-sonnet-5.5 | 390k → 131k | 68k → 65k | $0.319 → $0.273 | 10 → 7 | v6 Batch, v6 Batch |
  | opencode-deepseek-v4.1-flash-1017 | 165k → 141k | 60k → 32k | $0.015 → $0.010 | 8 → 9 | v5, v5 |
  | opencode-glm-5.3-flash | 216k → 200k | 54k → 64k | $0.002 → $0.021 | 9 → 10 | v6 Batch, v6 Batch |
  | opencode-gpt-6.1-terra | 683k → 1.46M | 53k → 64k | $0.151 → $0.214 | 32 → 58 | REST, v5 |

  "v5" is the v5 client's `ObjectsBatcher`, and "REST" is hand-written
  client-side batches against `/v1/batch/objects`.

  - Page format shows in tokens where the harness keeps the whole page.
    OpenCode's `webfetch` with `format: markdown` returns every code tab of
    an HTML page (25–41k characters each), and OpenCode Sonnet's total
    input fell by two thirds on the same five pages. Agents that read only
    the five pages otherwise changed by 10–15%.
  - The largest drops came from work beyond reading. Claude Code Haiku's
    baseline downloaded the Go v6 module and a Go toolchain; its Markdown
    Trial did not. GPT 6.1 Terra installed the Python and TypeScript
    clients and type-checked its code in both arms, more in the Markdown
    one. Neither is attributable to the page format at n=1.
  - The C6 contradiction split the Go answers: 9 of 14 used v6
    `collection.Batch`, 4 the v5 `ObjectsBatcher`, and 1 REST batches. Each
    of those 5 answers repeats the concepts page's claim that Go lacks
    server-side batching, and both GPT answers name the conflict. GLM 5.3
    Flash wrote v5 in both Pi Trials and v6 in both OpenCode Trials, so the
    harness's page extraction may decide which page wins.

### Fixed-page reading with other sources ruled out

- Change: the index-import-pages prompt adds "Use only these pages: don't
  fetch other URLs, install packages, or run code to check your answer."
  (Task fingerprint `4a44ecd7918f`). Same 7 Agents and arms, two Trials
  per arm, run locally on 2026-10-29.
- Result: 28 Trials passed. One more OpenCode DeepSeek baseline Trial was
  killed (exit 137) 13 seconds in, with 10 Trials sharing the Docker VM.
  It is a non-result, excluded, and rerun. No Trial used a non-docs URL or
  installed anything, and Trials made 7–16 tool calls.
- Metric: characters that tool calls returned, read from each transcript,
  and for Claude Code the input tokens of the Haiku requests in which
  `WebFetch` summarises pages.

  | Harness | What the model reads | HTML | Markdown |
  |---|---|---|---|
  | OpenCode (all 4 models) | `webfetch` output, 5 pages | 146,910–147,019 chars | 116,121–116,154 chars |
  | OpenCode | context on the turn after the reads | 41–68k tokens | 33–55k tokens |
  | Claude Code Sonnet | summarizer input | 41.6k tokens | 33.0k tokens |
  | Claude Code Sonnet, Haiku | `WebFetch` summaries | 8–11k chars | 10–16k chars |

  - The Markdown pages cut what each harness reads by about a fifth, and
    the figure barely varies between Trials: OpenCode's `webfetch` output
    is the same for every model.
  - Total input is that context re-sent on every later turn, so the turn
    count decides it. OpenCode GPT 6.1 Terra took 9 turns on Markdown
    (four `todowrite` calls) against 3–4 on HTML, and its mean total input
    rose from 112k to 268k. OpenCode Sonnet took 4 turns against 3 (155k to
    196k). OpenCode DeepSeek (187k to 137k) and GLM (178k to 133k) fell.
  - Claude Code's main model sees only summaries, so its total input
    barely moved (Sonnet 121k to 117k, Haiku 189k to 183k). One Opus
    Markdown Trial fetched the `.md` pages with `curl` and read them whole
    (129k characters in the main context), and Opus's mean rose from 299k
    to 392k.
  - OpenCode reported zero cost for both GPT 6.1 Terra Markdown Trials;
    unexplained.
- Conclusion: report what the harness read (fetched characters, context
  after the reads, summarizer input) as the token effect of a page-format
  change. Total input and cost measure agent behaviour and need many more
  Trials to compare.

### Iteration 2: per-language code pages (B6), three languages

- Change: the docs repo's `feat/markdown-export-iter2` (3a5fd3b0, from
  iter1). A tab group whose panels are all languages keeps its Python panels
  inline under a line linking the same section on each other language's code
  page, `<route>.<language>.md`. A note under each title links every code
  page. The build writes 586 code pages, and the landing pages total 19.8%
  less than iter1's.
- Run: index-import-pages, `markdown-docs-iter1` against
  `markdown-docs-iter2`, 7 Agents, two Trials per arm, local, 2026-10-30.
  The iter2 prompt also allows "the code example pages they link to", since
  "no others" would forbid the pages holding the TypeScript and Go code.
- Result: 24 Trials passed. 4 are non-results: both OpenCode GLM iter1
  Trials (`apt-get` could not reach Debian in setup), and one OpenCode
  DeepSeek iter1 and one OpenCode Sonnet iter2 Trial (OpenRouter 402, "would
  exceed your available credits given your current in-flight requests",
  recorded as `timed-out`).

  | Agent | iter1 input | iter2 input | Code pages fetched |
  |---|---|---|---|
  | Claude Code Haiku | 185k, 226k | 284k, 314k | 5–6, with Python |
  | Claude Code Sonnet | 114k, 118k | 167k, 176k | 6 |
  | Claude Code Opus | 360k, 380k | 377k, 390k | 7, or none |
  | OpenCode Sonnet | 130k, 130k | 184k | 8 |
  | OpenCode DeepSeek | 287k | 195k, 190k | 8 |
  | OpenCode GLM | (none graded) | 334k, 236k | 7–8 |
  | OpenCode GPT 6.1 Terra | 270k, 191k | 447k, 324k | 8 |

  - Agents found the code pages, and most fetched every one, including the
    Python pages, which repeat the landing page, and Go v5. OpenCode made
    14–15 fetches against 6 and read 125,634–126,038 characters against
    116,121–116,154.
  - Both OpenCode DeepSeek iter2 Trials wrote Go v5 code; its graded iter1
    Trial wrote v6. `import.go.md` has only the server-side batching example
    and lists 7 sections without a Go example.
  - The prompt's added phrase may itself invite fetching every code page.
- Conclusion: for a reader of several languages, the split costs more turns
  than the smaller pages save. Not shipped.

### Iteration 2 for a Python-only reader: index-import-pages-python

- Run: the new `investigate/index-import-pages-python` (the same pages,
  Python only), baseline HTML, `markdown-docs-iter1`, and
  `markdown-docs-iter2`, with prompts that differ only in their URLs. 7
  Agents, two Trials per arm, local, 2026-10-30.
- Result: 22 Trials passed. 20 are non-results from Agent setup, on the
  first run and again on the rerun: `apt-get` and `curl` network errors,
  then 360-second setup timeouts while deb.debian.org was slow. No OpenCode DeepSeek, GLM, or GPT Trial was
  graded. No iter2 Trial fetched a code page.

  | Agent | Measure | HTML | iter1 | iter2 |
  |---|---|---|---|---|
  | OpenCode Sonnet | `webfetch` output | 146,903 chars | 116,121 | 90,704 |
  | Claude Code Sonnet | summarizer input | 41.6k | 33.0k | 25.2k |
  | Claude Code Sonnet | total input | 118k, 120k | 109k, 111k | 102k, 103k |
  | Claude Code Haiku | total input | 175k | 170k, 172k | 163k, 160k |
  | OpenCode Sonnet | total input | 150k | 125k, 186k | 105k, 154k |
  | Claude Code Opus | total input | 216k, 204k | 160k, 535k | 110k, 225k |

- Conclusion: for a single-language reader, iter2 cuts what the harness reads
  by about a fifth against iter1, and total input by 5–7% where the Trials
  are consistent. Together with the three-language run, turn count decides
  total input more than page size does, so iter1 ships and iter2 does not.

### Iteration 3: Go v6 before Go v5, Go v5 labelled legacy (B3)

- Change: the docs repo's `feat/markdown-export-iter3` (880e14ef, from
  iter1). The export moves each Go v5 panel to just after Go v6; in the
  build, v6 directly precedes v5 in 208 places and never follows it. The
  `gov5` label is "Go (v5, legacy)" in the HTML and the Markdown. The
  build does not include weaviate/docs#587 (C1, C6), so `concepts/data-import`
  still says "The Go client does not yet support them".
- Run: index-import-pages, `markdown-docs-iter1` against
  `markdown-docs-iter3`, OpenCode GPT 6.1 Terra, OpenCode DeepSeek, and
  Claude Code Sonnet (the Agents that had written v5), two Trials per arm,
  local, 2026-10-31.
- Result: 11 Trials passed; one OpenCode GPT iter1 Trial is a non-result
  (`apt-get` network error). Go client used, read from each `findings.json`:

  | Agent | iter1 import | iter3 import | iter1 collection | iter3 collection |
  |---|---|---|---|---|
  | OpenCode GPT 6.1 Terra | v5 | v5, v5 | v5 | v5, v5 |
  | OpenCode DeepSeek | v5, v6 | v5, v6 | v5, v6 | v5, v6 |
  | Claude Code Sonnet | v6, v5 | v6, client-side | v5, v5 | v6, v6 |

  - Every v5 or client-side import in iter3 follows the concepts page. Both
    GPT Trials name the conflict and pick v5 as "the explicitly documented
    Go v5 fallback". The DeepSeek and Sonnet ones repeat "the Go client does
    not support server-side batching".
  - Claude Code Sonnet's iter3 client-side Trial wrote "the docs pages read
    give no Go batch code": its `WebFetch` summary left out the v6 panel.
- Conclusion: panel order and the label did not change the import answers;
  the concepts page's claim drives them. Sonnet's collection code moved to
  v6 in both iter3 Trials, a weak sign at two Trials. Re-measure on a build
  that includes weaviate/docs#587.

### HTML against iter1 on the same content, after weaviate/docs#587

- Change: weaviate/docs#587 (C1, C6) reached docs.weaviate.io, so the HTML
  baseline says Go v6 supports server-side batching. The docs repo's
  `feat/markdown-export-iter1-main` (7f887cf5) is iter1 rebased onto that
  `main`, so both arms carry the same content. Its last commit reads the
  Scalar spec URL from `configuration.url`, which #588 moved; without it the
  export wrote no API reference pages.
- Run: index-import-pages, baseline against `markdown-docs-iter1-main`,
  Claude Code Sonnet and OpenCode Sonnet, DeepSeek, GLM, and GPT 6.1 Terra,
  three Trials per arm, local, 2026-10-31. This is the run proposed in
  `plan/docs-experiments-review.md`, with three Trials instead of five, and
  the GPT arm added. #587 had shipped by then, so it measures format on the
  corrected content rather than the old sentence.
- Result: 27 Trials passed. 3 are non-results: OpenCode Sonnet HTML
  `3JmVLCw` and OpenCode GLM Markdown `GK2kAsa` exited with 137, an
  out-of-memory kill that Harbor labelled `ApiRateLimitError`, and OpenCode
  GPT HTML `R8cURuo` failed `apt-get` in setup. Runs:
  `experiment-outputs/20261031-11*__investigate__index-import-pages__*`.

  | Agent | Import, HTML | Import, Markdown | Input, HTML | Input, Markdown | Turns |
  |---|---|---|---|---|---|
  | Claude Code Sonnet | v6 ×3 | v6 ×2, v6 and v5 ×1 | 122k, 122k, 124k | 113k, 114k, 119k | 9 and 9 |
  | OpenCode Sonnet | v6 ×2 | v6 ×3 | 157k, 155k | 129k, 130k, 128k | 3 and 3 |
  | OpenCode DeepSeek | v6 ×3 | v6 ×3 | 170k, 168k, 236k | 172k, 201k, 188k | 5–6 and 5–6 |
  | OpenCode GLM | v6 ×3 | v6 ×2 | 302k, 323k, 290k | 145k, 145k | 6–8 and 5 |
  | OpenCode GPT 6.1 Terra | v6 ×2 | v6 ×3 | 378k, 436k | 272k, 234k, 272k | 10–11 and 8–9 |

  - Go: every graded Trial in both arms imports with Go v6. Before #587,
    batch 2 had 4 of 15 HTML and 8 of 14 Markdown Trials using only v6
    (regex count). Fixing the concepts page removed the v5 imports in both
    formats, so a format effect on the Go import can no longer be measured.
    A few collection-creation snippets still use v5 (one in each arm for
    Claude Code Sonnet and for GPT).
  - What the harness reads fell as before: OpenCode `webfetch` output
    146,976 to 116,242 characters (−21%), Claude Code's summarizer input
    41.6k to 33.1k tokens (−20%). Two OpenCode GLM HTML Trials fetched more
    (206k and 209k characters).
  - Total input was lower on Markdown for all five Agents: −2% for DeepSeek
    and −6% for Claude Code Sonnet, where turns matched; −17% for OpenCode
    Sonnet; −36% for GPT and −52% for GLM, which also took fewer turns. In
    batch 2, GPT took more turns on Markdown (9 against 3–4); here it took
    fewer (8–9 against 10–11), so its turn count varies more between
    batches than with the format.
  - OpenCode reported $0 cost for 3 GPT Trials, as before.
- Conclusion: on the same content, Markdown cuts what each harness reads by
  about a fifth and did not raise total input for any Agent. The Go import
  accuracy problem was the content, which #587 fixed.

### Markdown from the normal page URLs (content negotiation)

- Change: none to the build. The `markdown-docs-negotiation` Treatment gives
  the baseline prompt with the `markdown-docs-iter1-main` host and the normal
  page URLs, no `.md`. The build offers Markdown three ways: `Accept`
  negotiation, a `<link rel="alternate" type="text/markdown">`, and a hidden
  notice that names the `.md` URL on the production host (404 until shipped).
- Run: index-import-pages, `markdown-docs-negotiation`, Claude Code Sonnet
  and Opus, OpenCode Sonnet, GLM and GPT 6.1 Terra, Pi Sonnet and GLM, two
  Trials each, local, 2026-10-31. All 14 passed. Runs:
  `experiment-outputs/20261031-12*__*+markdown-docs-negotiation`. Analysis:
  the session scratchpad's `discovery-tabloss/run-a/report.md`.
- Result: 61 of 98 docs fetches returned Markdown.
  - Claude Code WebFetch and OpenCode `webfetch` got Markdown on all 50
    built-in fetches. Claude Code's summarizer input was 33.1k tokens in all
    four Trials, as with explicit `.md` URLs (HTML: 41.6k). OpenCode received
    116,242 characters per Trial, the `.md` figure.
  - Pi got HTML on all 30 fetches, so its extraction still dropped the
    TypeScript and Go tabs. Both Pi Sonnet Trials wrote v5 Go "from my own
    knowledge".
  - Opus also curled every page: one Trial sent `Accept: text/markdown`
    unprompted and got Markdown, the other got HTML.
  - No Agent acted on the notice or the `<link>`. Two saw the notice and
    carried on with HTML. The one Trial that fetched `.md` URLs (OpenCode
    GLM) cited a truncated `<link>` and the "markdown-export" in the draft's
    host name.
  - OpenCode GLM's "middle truncated" re-reads also happen on Markdown: one
    Trial used 799k input tokens.
- Conclusion: negotiation alone delivers Markdown to Claude Code and OpenCode
  with the same savings as `.md` URLs. It does not reach Pi, and the notice
  and link did not change any Agent's behaviour.

### Tab loss in HTML extraction: Pi against OpenCode

- Question: when a harness's HTML extraction drops the inactive code tabs,
  do its TypeScript and Go answers get worse? Inactive tabs are wrapped in
  `style=display:none aria-hidden=true`, which Readability-style extraction
  removes. Pi's extraction drops them; OpenCode's conversion keeps them.
  Comparing the two harnesses on HTML and Markdown, with the same models,
  separates tab loss from other format effects. Python, which every arm sees,
  is the control.
- Run: index-import-pages, baseline against `markdown-docs-iter1-main`, Pi
  and OpenCode each with Sonnet, DeepSeek and GLM, plus Claude Code Sonnet,
  five Trials per arm, local, 2026-10-31. 74 launched. 70 graded, all
  passed. 4 non-results: OpenCode Sonnet and DeepSeek HTML exit 137 kills
  (two each) with two arms running at once; their reruns, one arm at a time,
  passed. Runs: `experiment-outputs/20261031-125918*` to `20261031-133111*`
  (the last two are the reruns). Scoring: an
  offline scorer over `findings.json` (the session scratchpad's
  `discovery-tabloss/scorer/`; 293 of 294 agreement with the hand labels). A
  language counts as current when its collection and import code both use
  the current client API as the pages show it.

  | Harness | Arm | Python | TypeScript | Go |
  |---|---|---|---|---|
  | Pi (Sonnet, DeepSeek, GLM) | HTML | 15/15 | 7/15 | 3/15 |
  | Pi | Markdown | 15/15 | 15/15 | 15/15 |
  | OpenCode (Sonnet, DeepSeek, GLM) | HTML | 15/15 | 15/15 | 15/15 |
  | OpenCode | Markdown | 15/15 | 15/15 | 15/15 |
  | Claude Code Sonnet | HTML | 5/5 | 5/5 | 3/5 |
  | Claude Code Sonnet | Markdown | 5/5 | 5/5 | 4/5 |

  - Pi HTML against Pi Markdown: Go p = 0.00001, TypeScript p = 0.002
    (Fisher's exact). OpenCode shows no difference, and Python is 15/15 in
    every cell.
  - The 3 Pi HTML Trials with current Go are the 3 that re-fetched a page in
    `mode: "raw"` and parsed the `codeBlockContainer` elements themselves.
    The other 12 say the pages showed "only Python" and wrote Go "from
    memory": v5, or v6 calls under v5 import paths. Pi DeepSeek used Python's
    `batch.stream` in TypeScript in 4 of 5 HTML Trials.
  - Claude Code's misses are v5 collection-creation snippets (2 HTML, 1
    Markdown). Its imports are current in all 10.
- Conclusion: tab loss is real and large for Pi. Markdown fixes it when the
  agent fetches `.md` URLs, but Pi does not negotiate (previous entry), so
  on docs.weaviate.io Pi needs either the `.md` URL or HTML whose inactive
  tabs survive extraction.

## Proposals

Each item says what to change, where, the evidence from iteration 0, and how
to evaluate it. Sizes are from the local build (`build/**/*.md`, 423 pages,
6,122,370 characters, built 2026-10-29 11:16) unless a staging URL is named.

### Build changes (Markdown export only, HTML unchanged)

These change how the export writes pages, not what the docs say. They should
reduce tokens without changing answers, so a token comparison against the
current staging build evaluates them.

#### B1. Write tables without column padding

Applied in iteration 1.


- Change: `src/plugins/markdown-export/html-to-markdown.mjs:111`, from
  `.use(remarkGfm)` to `.use(remarkGfm, { tablePipeAlign: false })`.
  remark-gfm 4.0.1 pads every cell to its column's widest cell by default.
- Evidence: re-stringifying the built pages with that option shrinks
  `release-notes.md` from 28,099 to 12,437 characters (56%), and all 423
  pages by 7.3% (446k characters). `deploy/configuration/env-vars.md` has
  79,624 characters of padding.
- Output: delimiter rows become `| - | - | - |`, and cells keep one space on
  each side. `tableCellPadding: false` saves another 660 characters on
  release-notes; I would not use it.
- Risk: none for Markdown readers; a padded table renders the same.

#### B2. Shorten long vector literals in code blocks

Applied in iteration 1. The sentence goes after the block, not before it,
so each tab's bold label stays next to its fence.


- Change: a remark transform in the export, after `rehypeRemark`. In each
  `code` node, replace a bracketed run of 16 or more numeric literals with
  its first three values and `...`. Add one line of prose before the block:
  "This example's 1,536-number vector is shortened to its first three
  values." The HTML keeps the full vector for copying.
- Identification: the pattern `\[\s*(?:NUM\s*,\s*){15,}NUM\s*,?\s*\]`. Across
  every code block in the build, it matches only 300- and 1,536-number
  vectors (7 blocks on 5 pages) and no other array.
- Evidence: 120,717 characters across the build (2%), concentrated on
  `starter-guides/custom-vectors.md` (58,524 of 80,881), `search/hybrid.md`
  (34,426 of 85,393), and `search/similarity.md` (20,945 of 66,062).
- Why not at the source: the literals are in tested snippet files
  (`_includes/code/howto/search.similarity-v3.py:228`,
  `search.hybrid-v3.py:559`, `quickstart.byov.all.py:47`, and 11 more
  places). They run against a live instance, so shortening them breaks the
  tests. Loading the vector from a fixture changes what HTML readers see in
  14 places, while the export transform changes one file.

#### B3. Put Go v6 before Go v5 in each code tab group

- Change: in the export's code-tab handler (`html-to-markdown.mjs:188`),
  order the `Go (v6)` panel before `Go (v5)`. Optionally relabel `gov5` as
  "Go (v5, legacy)" in `src/theme/Tabs/index.js:30`, which changes the HTML
  label too.
- Evidence: v5 comes before v6 on 75 of the 78 pages with a v5 tab, because
  each page's MDX lists v5 first. In the first matrix, DeepSeek's Markdown
  Trial submitted v5 code. In iteration 0, two of three DeepSeek Markdown
  Trials spent a fetch on `client-libraries/go.md` to decide, and Claude
  Code's `WebFetch` summary of the HTML quickstart returned only the v5 tab.
- Expected effect (inferred): fewer v5 answers and one fewer fetch.
- Result: tested in iteration 3 with the relabel. No change in the import
  answers while `concepts/data-import` still says Go lacks server-side
  batching (C6).

#### B4. Link to Markdown pages from Markdown pages

- Change: in `rewriteForMarkdown` (`html-to-markdown.mjs:298`), rewrite a link
  to a docs route as that route's `.md` path (`markdownPathForRoute`). On
  Netlify previews, use `DEPLOY_PRIME_URL` as the link host, so a staging
  page links to staging. Keep the frontmatter `url:` as the canonical HTML
  URL.
- Evidence: every `.md` page links to docs.weaviate.io HTML pages, 54–112 links
  per Trial's pages. No Trial followed one: every agent built `.md` URLs by
  hand, and some guessed wrong paths. The REST pages already link to
  `.md` (`api/rest.md`, 28 links), which on docs.weaviate.io redirect to the
  HTML REST page today.
- Expected effect: fewer guessed paths. Pi's `fetch_content` on a followed
  HTML link returns only the Python tab, so following links also matters for
  correctness.

#### B5. Answer a missing `.md` path with a short text 404 or its redirect

- Change: in `netlify/edge-functions/markdown-negotiation.ts`, when a `.md`
  path has no file, check the HTML path's redirect. If the HTML path
  redirects, redirect to the target's `.md`. Otherwise return a
  `text/plain` 404 of one or two lines that names the path and a starting
  page.
- Evidence: on staging today, `weaviate/manage-data/import.md`,
  `weaviate/deploy.md`, and any unknown `.md` return the 14,298-character
  HTML 404 page. The HTML path `weaviate/manage-data/import` redirects to the
  batch import page. In SFQFhiY, one such 404 stayed in context for four more
  requests, about 14k input tokens.

#### B6. Per-language Markdown (larger; after B1–B5)

- Change: serve `?lang=py,ts,go` (edge function filtering the labelled
  fences) or per-language files.
- Evidence: code is 37% of the build's characters. Java, C#, Go v5, and Curl
  fences were 20–29% of what Claude Code's Markdown Trials retrieved.
  `quickstart.md` is 68,920 characters, above Pi's 30,000-character fetch
  limit, so DeepSeek read it in two or three slices.
- Risk: agents must discover the parameter. Without a link or a note on each
  page, they will not use it.
- Result: per-language files were tested in iteration 2. Linked from each
  page, they were found and fetched for every language, which cost more
  than it saved for a reader of several languages.

### Content changes (docs text, both HTML and Markdown)

These change what agents answer, so check pass rates and the answers evaluate
them, not only tokens.

#### C1. Generate the version tables from build-time values

- Change: the "Latest patch" table at
  `docs/weaviate/release-notes/index.md:20` is hand-written and says
  `v1.40.0`. `_build_scripts/update-config-versions.js` already fetches the
  latest releases from GitHub at build time for `||site.weaviate_version||`,
  which the Python client page uses. Fill the table from those values, and
  add a "Latest versions" list (server and each client) beside it, as you
  proposed.
- Evidence: all 7 Python client failures copied "4.24.x" from the
  compatibility table, and both Weaviate version failures copied 1.40.0 from
  the "Latest release" row. Since commit 8dd9fbe, "4.24.x" passes; 1.40.0
  still fails.
- Check first: whether `||site.*||` substitution works inside a Markdown
  table and inside `_includes/release-history.md`.

#### C2. Put each client's version on the client index

- Change: on `client-libraries` (`docs/weaviate/client-libraries/index.mdx`),
  add the version to each client's line using the same build-time values:
  `[Python Client](...) (latest: v4.24.1): Install and use...`.
- Evidence: `client-libraries.md` is 1,887 characters with no versions.
  hS8RtcW and r98NFU6 read it, reported "no specific version numbers are
  listed", and stopped.

#### C3. Say "start with hybrid" where agents look for search

- Change: one sentence and a link to `search/hybrid` in quickstart Step 2
  ("Semantic (vector) search") and the `search/basics` introduction.
- Evidence: all 12 client-code-examples Trials copied `nearText` from the
  quickstart. None opened `search/hybrid` or the search concepts page, where
  the "good default" statement is. `search/basics.md` lists vector, keyword,
  and hybrid search as peers.
- Evaluation: the hybrid check was removed in 8dd9fbe, so this needs reading
  the `search` answers, or the LLM judge in `plan/TODO.md`.

#### C4. Show server-side batching in the Go and TypeScript examples

- Change: use `collection.Batch(ctx, ...)` in the quickstart's Go v6 import
  and the Go client page's "Get started". Remove the TypeScript client page's
  note that "The TS client does not have a `batch` method yet / We use
  `insertMany`", which the import page contradicts (`data.ingest`).
- Evidence: all 12 Go answers used `Data.Insert`; two TypeScript answers
  called `insertMany` server-side batching. Both trace to these examples.
- Evaluation: not scored; read the `config_ingestion` answers.

#### C5. Check llms.txt versions for drift

- Change: `weaviate.io/llms.txt` is hand-maintained in the weaviate-io repo
  (`.github/workflows/llms_txt_snippet_sync.yml:3`). The snippet drift check
  covers code, not versions. Compare its version lines with the build-time
  values, or generate them.
- Evidence: it states "Weaviate Server (OSS): v1.39.1+" and "Python client:
  v4.23.0+" (read by hS8RtcW). Staging's `/llms.txt` returns 301; no Trial
  read it.

#### C6. Say that Go v6 supports server-side batching

- Change: `docs/weaviate/concepts/data-import.mdx` says "Server-side batch
  imports are supported by the Python, TypeScript, Java, and C# clients. The
  Go client does not yet support them; use client-side batching instead."
  `manage-objects/import` shows server-side batching in its Go (v6) tab and
  says only the Go v5 client lacks it. Name Go v6 among the supported
  clients, and Go v5 as the exception.
- Evidence: found while building `investigate/index-import-pages`, whose
  fixed pages include both. docs.weaviate.io has the same sentence. In that
  Task's first batch, 5 of 14 Go import answers used client-side batching
  and each repeated this sentence's claim (log, "Fixed-page reading").
- Evaluation: that Task's Go `batch_import` answers.

### Evaluating them

1. B1 and B2 together as iteration 1: both only delete characters. One
   staging deploy; n=3 with `claude-code-sonnet-5.5` and
   `pi-deepseek-v4.1-flash-1017` on both Tasks, with the baseline and the
   current staging build rerun in the same batch, since the Tasks read the
   live web.
2. B3, B4, and B5 as iteration 2. B4 needs a new Treatment prompt: its links
   then point to staging `.md`, so the 404 caveat no longer applies.
3. C1–C4 after the token changes are measured, in production docs as well:
   they fix answers on both arms.

Compare total input (including Claude Code's `WebFetch` summarizer),
uncached input, and cost, not main-model input alone.
