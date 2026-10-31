# markdown-docs-iter2

Iteration 2 of the docs feedback loop (`plan/docs-improvements.md`): the
`markdown-docs-iter1` build with language tab groups split out, in the docs
repo's `feat/markdown-export-iter2` branch (3a5fd3b0). Each page keeps the
Python examples inline under a line that links the same section on each other
language's code page, `<route>.<language>.md`. Tab groups that are not
languages, such as Docker/Kubernetes, stay inline.

Question, for `investigate/index-import-pages`: against
`markdown-docs-iter1`, does moving non-Python examples to code pages reduce
the tokens an Agent spends, at the same check results, and do Agents find the
TypeScript and Go examples through the links? Run `markdown-docs-iter1` in the
same batch, since both Treatments read the live web.

`investigate/index-import-pages-python` asks the same question for a reader
who needs only Python, whose examples stay inline. Its prompt matches
`markdown-docs-iter1`'s except for the host.

The `index-import-pages` prompt matches `markdown-docs-iter1`'s except for
the host, `feat-markdown-export-iter2--docs-weaviate-io.netlify.app`, and two
phrases that also allow "the code example pages they link to". Without them the
prompt's "no others" would forbid the pages that now hold the TypeScript and
Go examples. The phrases name no language or path, so finding the code pages
is still up to the Agent.
