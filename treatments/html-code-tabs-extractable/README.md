# html-code-tabs-extractable

The docs site's HTML with inactive code tabs hidden only by a stylesheet
class, in the docs repo's `fix/code-tabs-extractable` branch (from `main` at
8d1d02d2, after weaviate/docs#587). On docs.weaviate.io, inactive tab panels
carry inline `display:none`, `aria-hidden="true"` and the class
`tabPanelHidden`; Readability-based extraction, which Pi's `pi-web-access`
uses, drops all three, so Pi sees only the first language. The branch
replaces them with the class `tabPanelInactive` (`display: none` in the
stylesheet) and a `data-tab-inactive` attribute. The draft has no Markdown
export.

Question, for `investigate/index-import-pages` with Pi Agents: against the
baseline (docs.weaviate.io HTML), do Pi's TypeScript and Go answers use the
current client APIs once every code tab survives extraction? Pi's extraction
of the five pages should grow from about 83k to about 116k characters and
include TypeScript and Go code. Compare with the Pi baseline and
`markdown-docs-iter1-main` Trials of the same day (`20261031-12*` and
`20261031-13*`).

The prompt matches the baseline `instruction.md` except for the host,
`fix-code-tabs-extractable--docs-weaviate-io.netlify.app`.
