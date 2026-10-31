# markdown-docs-iter3

Iteration 3 of the docs feedback loop (`plan/docs-improvements.md`, proposal
B3): the `markdown-docs-iter1` build with two changes, in the docs repo's
`feat/markdown-export-iter3` branch (880e14ef):

- the Markdown export moves each Go v5 panel to just after the Go v6 panel,
  where the MDX lists v5 first (75 of the 78 pages with a v5 tab);
- the `gov5` tab label is "Go (v5, legacy)" in both the HTML and the
  Markdown.

Question, for `investigate/index-import-pages`: against
`markdown-docs-iter1`, do fewer Go answers use the v5 client when v6 comes
first and v5 is labelled legacy? Read each Go answer: v6 `collection.Batch`
or v5 `ObjectsBatcher`, and the reason given. Run `markdown-docs-iter1` in
the same batch, since both Treatments read the live web.

The build does not include the docs fix for `concepts/data-import`, which
says "The Go client does not yet support them" of server-side batching
(weaviate/docs#587). An answer that repeats that sentence followed the
concepts page, not the panel order.

The prompt matches `markdown-docs-iter1`'s except for the host,
`feat-markdown-export-iter3--docs-weaviate-io.netlify.app`.
