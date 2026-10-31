# markdown-docs-negotiation

The `markdown-docs-iter1-main` build, read through the normal page URLs
instead of the `.md` URLs. The build offers Markdown three ways, in the docs
repo's `feat/markdown-export-iter1-main` branch (7f887cf5):

- a request whose `Accept` header ranks `text/markdown` at or above
  `text/html` gets the page's Markdown from the normal URL
  (`netlify/edge-functions/markdown-negotiation.ts`);
- each HTML page has `<link rel="alternate" type="text/markdown">` to its
  `.md` URL;
- each HTML page has a visually hidden notice naming the `.md` URL. The
  notice uses the production host, so on the draft it points to
  `https://docs.weaviate.io/<route>.md`, which does not exist yet and returns
  404.

Question, for `investigate/index-import-pages`: when the prompt names the
normal page URLs, as a user would, which Agents receive Markdown, and by
which mechanism? Read each docs fetch in the transcript: the size or content
type of what came back (Markdown pages are 4.5 to 33 KB, HTML 33 to 428 KB),
and any `.md` fetch that follows the link or notice. Compare tokens with the
same Agents' baseline and `markdown-docs-iter1-main` Trials in the
`20261031-11*` batch, which read the same content.

The prompt matches the baseline `instruction.md` except for the host,
`feat-markdown-export-iter1-main--docs-weaviate-io.netlify.app`.
