# weaviate-docs

Question: does a local Markdown copy of the Weaviate docs pages agents read
reduce the tokens `investigate/current-practices` takes? Compare `usage` in
`weval.json` (`cost_usd`, `n_output_tokens`, uncached input) against baseline
Trials of the same Agent and prompt variant.

The pages are the ones baseline Claude Code Trials fetched most often (15
Trials from 20 and 21 October). Each page starts with its source URL so
answers can cite it.

`fetch_pages.py` regenerates `pages/` from the live site. The committed
pages were fetched on 2026-10-27. They copy the docs as published, including
the release-notes tables that give the latest server patch as `v1.40.0`
(1.40.2 was out) and Python clients by minor line (`4.24.x`).
