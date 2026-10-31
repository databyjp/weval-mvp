# markdown-docs-iter1-main

The `markdown-docs-iter1` export rebased onto the docs repo's `main` after
weaviate/docs#587, in the `feat/markdown-export-iter1-main` branch
(7f887cf5). The Markdown and docs.weaviate.io now carry the same content,
including #587's statement that the Go v6 client supports server-side
batching. The last commit reads the Scalar spec URL from its new location
after #588.

Question, for `investigate/index-import-pages`: against the baseline (HTML
on docs.weaviate.io), does serving the same content as Markdown change which
Go client Agents use, or the tokens they spend? Before #587, the baseline
used Go v6 for the import less often than iter1, with both builds still
saying the Go client lacked server-side batching. Run the baseline in the
same batch, since both arms read the live web.

The prompt matches `markdown-docs-iter1`'s except for the host,
`feat-markdown-export-iter1-main--docs-weaviate-io.netlify.app`.
