# markdown-docs-staging

Questions, each against a baseline that starts from docs.weaviate.io:

- `investigate/docs-token-usage`: does serving the Weaviate docs as Markdown
  reduce the tokens an Agent spends, at the same check results? Compare
  `usage` in each Trial's `weval.json`.
- `investigate/client-code-examples`: does it raise the pass rate when the
  Agent needs TypeScript and Go code? The HTML hides every tab but the
  default Python one; the Markdown pages carry all of them.

Each prompt points at the `feat-markdown-export` staging build of the docs,
which serves a Markdown version of each page at its path plus `.md`. Some
links inside the Markdown pages point to `.md` paths on docs.weaviate.io,
which return 404, so the prompt tells the Agent to rewrite them.

Claude Code's `WebFetch` returns a smaller model's answer to the Agent's
prompt about the page, not the page itself, and its tokens count in the
Trial's `usage`.
