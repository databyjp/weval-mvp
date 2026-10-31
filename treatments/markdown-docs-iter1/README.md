# markdown-docs-iter1

Iteration 1 of the docs feedback loop (`plan/docs-improvements.md`): the
`markdown-docs-staging` build with two changes to the Markdown export, in
the docs repo's `feat/markdown-export-iter1` branch (980bd35a):

- tables are written without padding cells to the column width;
- vector literals of 16 or more numbers in code blocks keep their first three
  values, with a sentence after the block that says so.

Question, for `investigate/docs-token-usage`,
`investigate/client-code-examples`, `investigate/index-import-pages`, and
`investigate/index-import-pages-python`:
against `markdown-docs-staging`, do these changes reduce the tokens an Agent
spends, at the same check results? Run
the baseline and `markdown-docs-staging` in the same batch, since both Tasks
read the live web.

The prompts match `markdown-docs-staging`'s except for the host,
`feat-markdown-export-iter1--docs-weaviate-io.netlify.app`, so the build is
the only difference between the two Treatments.
