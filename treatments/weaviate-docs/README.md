# weaviate-docs

Question: does a local Markdown copy of the Weaviate docs pages agents read
reduce the tokens `investigate/current-practices` takes? Compare `usage` in
`weval.json` (`cost_usd`, `n_output_tokens`, uncached input) against baseline
Trials of the same Agent and prompt variant.

The pages are the ones baseline Claude Code Trials fetched most often (15
Trials from 20 and 21 October). Each page starts with its source URL so
answers can cite it.
