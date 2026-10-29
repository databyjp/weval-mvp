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
    server-side batching, and both GPT answers name the conflict. GLM 5.3 Flash wrote v5 in both Pi Trials and v6 in both OpenCode
    Trials, so the harness's page extraction may decide which page wins.

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
- Expected effect (inferred, untested): fewer v5 answers and one fewer fetch.

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
