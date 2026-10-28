"""Stylesheet and logo embedded in every report page.

Each page carries its own copy so it opens on its own from ``file://``. The
palette and type follow the Weaviate brand guidelines
(``weaviate-design-assets``): navy ``#130C49`` on pale blue surfaces, brand
green/red/yellow for pass/fail/warn states, Plus Jakarta Sans headings with
Inter body text (fetched from Google Fonts, falling back to system fonts
offline), and the ``#55CDE0`` to ``#06CD00`` gradient as the page accent.
"""

# The brand "W" (Logos/SVG/W/w-dark-green.svg); the outline takes the page's
# text color so the mark reads on both themes.
LOGO = """<svg class="logo" viewBox="0 0 48 30" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<path d="M46.9908 19.2331V8.4006C46.9908 7.34504 46.4207 6.36735 45.494 5.83668L37.534 1.27123C36.1981 0.504074 34.523 1.45581 34.523 2.97859V14.5206L28.8694 11.3077C25.8439 9.58883 22.1196 9.5946 19.097 11.3193L13.4755 14.5321V2.98147C13.4755 1.45869 11.8005 0.506958 10.4646 1.27412L2.50452 5.83668C1.57785 6.36735 1.00781 7.34504 1.00781 8.4006V19.2446C1.00781 20.7645 1.79417 22.1777 3.0921 22.9939L10.3389 27.5507C12.2244 28.736 14.6565 28.6409 16.4397 27.3113L21.4765 23.5592C22.8621 22.5267 25.1277 22.5267 26.5133 23.5592L31.5501 27.3084C33.3333 28.6351 35.7654 28.7303 37.6509 27.5449L44.9065 22.9795C46.2044 22.1633 46.9878 20.7501 46.9878 19.2302H46.9908V19.2331Z" fill="#61BD73"/>
<path d="M46.0034 4.97391L38.0434 0.40846C37.1021 -0.133741 35.9737 -0.136625 35.0266 0.402692C34.0794 0.939125 33.5152 1.9024 33.5152 2.97815V12.7955L29.3759 10.4421C26.0492 8.55013 21.9186 8.5559 18.5949 10.4536L14.4877 12.8012V2.98103C14.4877 1.90528 13.9235 0.942009 12.9764 0.405576C12.0322 -0.130857 10.9038 -0.127973 9.95956 0.411344L1.99951 4.97391C0.765895 5.6805 0 6.99275 0 8.39728V19.2413C0 21.1102 0.952984 22.8262 2.55201 23.8298L9.79878 28.3895C10.8132 29.0298 11.9971 29.3672 13.2161 29.3672C14.5959 29.3672 15.9581 28.9202 17.0514 28.1069L22.0882 24.3547C23.123 23.5818 24.8711 23.5818 25.906 24.3547L30.9428 28.104C33.0504 29.6729 35.9649 29.7883 38.1954 28.3866L45.4509 23.8212C47.0178 22.8348 47.9649 21.165 48 19.3336V8.40016C48.0029 6.99275 47.237 5.6805 46.0034 4.97679V4.97391ZM13.1488 27.3772C12.342 27.3657 11.5703 27.1407 10.9096 26.7283L3.63654 22.1513C2.62509 21.5139 2.01998 20.4266 2.01998 19.2413V8.40016C2.01998 7.69934 2.4 7.04754 3.01389 6.69857L10.9739 2.13601C11.123 2.04948 11.2955 2.00334 11.4738 2.00334C11.6521 2.00334 11.81 2.04948 11.9678 2.13601C12.1169 2.21964 12.4648 2.47344 12.4648 2.9868V25.4853C12.4648 26.1832 12.7045 26.8437 13.1459 27.3772H13.1488ZM16.1686 26.2697L16.1364 26.2899C15.9552 26.4284 15.7476 26.4976 15.5255 26.4976C15.0256 26.4976 14.4877 26.1082 14.4877 25.4795V22.16L20.7552 18.2088C22.7342 16.96 25.2892 16.96 27.2682 18.2088L33.5298 22.16L33.5357 25.4766C33.5357 26.1053 32.9978 26.4947 32.4979 26.4947C32.2816 26.4947 32.0302 26.411 31.846 26.2726L27.1279 22.7598C25.3739 21.4534 22.629 21.4534 20.875 22.7598L16.1686 26.2697ZM28.3557 16.5303C25.716 14.8662 22.3045 14.8662 19.6648 16.5303L14.4848 19.795V15.1056L19.6034 12.1811L19.6239 12.1667C22.3191 10.6353 25.6663 10.6353 28.3674 12.1667L33.5152 15.094L33.524 19.7922L28.3557 16.5303ZM44.1033 22.307L37.1108 26.7081C36.4443 27.1292 35.6755 27.357 34.8745 27.3743C35.313 26.8408 35.5527 26.1803 35.5527 25.4824L35.5323 14.523V2.98103C35.5323 2.47344 35.8801 2.21676 36.0292 2.13024C36.1842 2.04083 36.3566 1.99757 36.5262 1.99757C36.6957 1.99757 36.8682 2.04083 37.0231 2.13024L44.9832 6.69569C45.5941 7.04754 45.9742 7.69934 45.9742 8.39728V19.2701C45.9625 20.4382 45.3574 21.511 44.3576 22.1398L44.0974 22.3042H44.1062L44.1033 22.307Z" fill="currentColor"/>
</svg>"""

STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

/* Weaviate brand palette. Muted text keeps at least 4.5:1 contrast on --bg,
   --stripe, and --band in both themes. The page sits on the brand pale blue,
   under a navy header in the brand dark gradient. */
:root {
  --bg: #ecf4f8; --surface: #ffffff; --fg: #130c49; --muted: #4e4b66;
  --line: #dde6f2; --line-strong: #b9c8de; --stripe: #ecf4f8; --hover: #e2eef7;
  --link: #0069b4; --code-bg: rgba(185, 200, 222, 0.28);
  --bar-required: rgba(97, 189, 115, 0.3); --bar-preferred: rgba(185, 200, 222, 0.3);
  --pass-fg: #1e6f38; --pass-bg: #d9f3cf; --fail-fg: #bb1627; --fail-bg: #fde3e5;
  --warn-fg: #6d5f00; --warn-bg: #faf4c0; --flag-fg: #4d2f9e; --flag-bg: #e7dff7;
  --cell-pass: #61bd73; --cell-fail: #f4404e; --cell-warn: #f0e447; --cell-none: #b9c8de;
  --accent: linear-gradient(90deg, #55cde0, #06cd00);
  --header: linear-gradient(90deg, #0c1428, #1b1464);
  --band: #e6f6fa; --panel: #f3f8fb; --pill-fg: #ffffff; --pill-bg: #130c49;
  --code-keyword: #6b2fb3; --code-string: #1e6f38; --code-name: #0069b4; --code-number: #a14600;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0c1428; --surface: #131c36; --fg: #ecf4f8; --muted: #a3aec9;
    --line: #243050; --line-strong: #3c4a73; --stripe: #16203e; --hover: #1c2a4e;
    --link: #7ad6eb; --code-bg: rgba(90, 105, 140, 0.35);
    --bar-required: rgba(97, 189, 115, 0.3); --bar-preferred: rgba(185, 200, 222, 0.2);
    --pass-fg: #8fe3a3; --pass-bg: rgba(97, 189, 115, 0.2); --fail-fg: #ff8a94; --fail-bg: rgba(244, 64, 78, 0.22);
    --warn-fg: #f1e96a; --warn-bg: rgba(249, 241, 93, 0.16); --flag-fg: #c9b8f0; --flag-bg: rgba(165, 144, 221, 0.22);
    --band: #1a2b4c; --panel: #16203e; --pill-fg: #0c1428; --pill-bg: #7ad6eb;
    --code-keyword: #c9b8f0; --code-string: #8fe3a3; --code-name: #7ad6eb; --code-number: #f2b36b;
  }
}
body { background: var(--bg); color: var(--fg);
  font: 14px/1.5 Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
  margin: 0; padding: 0 10% 32px; }
html { overflow-x: clip; }
@media (max-width: 600px) { body { padding: 0 16px 24px; } }
h1, h2, h3 { font-family: "Plus Jakarta Sans", Inter, system-ui, sans-serif; }
h1 { font-size: 20px; font-weight: 700; margin: 0; }
h2 { font-size: 20px; font-weight: 600; margin: 40px 0 10px; }
h2 .count, h3 .count { display: inline-block; vertical-align: 3px; margin-left: 6px; padding: 0 9px; border-radius: 999px;
  font: 600 12px/20px Inter, system-ui, sans-serif; color: var(--pill-fg); background: var(--pill-bg); }
h3 { font-size: 15px; font-weight: 600; margin: 16px 0 6px; }
h4 { font-size: 13px; font-weight: 600; margin: 12px 0 4px; color: var(--muted); }
p { margin: 0 0 8px; }
.intro { color: var(--muted); font-size: 13px; max-width: 90ch; margin: 0 0 16px; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
.mono, code, pre { font-family: Menlo, ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12.5px; }
code { background: var(--code-bg); border-radius: 4px; padding: 0 4px; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; margin: 0; }
.secondary, .muted { color: var(--muted); }

/* Source pages: Pygments token classes, one row per line. Every token color
   keeps 4.5:1 on --surface. */
.source .line { display: flex; min-height: 1.55em; line-height: 1.55; }
.source .line > span { min-width: 0; }
.source .linenos { flex: none; width: 4ch; margin-right: 14px; text-align: right;
  color: var(--muted); user-select: none; }
.source .linenos:hover { color: var(--fg); text-decoration: none; }
.source .line:target { background: var(--hover); }
.source .line:target .linenos { color: var(--fg); font-weight: 600; }
.source :is(.k, .kc, .kd, .kn, .kp, .kr, .kt, .ow) { color: var(--code-keyword); }
.source :is(.s, .s1, .s2, .sa, .sb, .sc, .sd, .se, .sh, .si, .sx, .sr, .ss, .dl) { color: var(--code-string); }
.source :is(.nf, .fm, .nc, .nn, .nd, .nt, .na) { color: var(--code-name); }
.source :is(.m, .mi, .mf, .mh, .mo, .mb, .il) { color: var(--code-number); }
.source :is(.c, .c1, .cm, .ch, .cs, .cp, .cpf) { color: var(--muted); font-style: italic; }
.source :is(.gh, .gu, .gs) { font-weight: 600; }
.source .ge { font-style: italic; }
.note { color: var(--muted); font-size: 12px; margin-left: 6px; }
.logo { height: 24px; width: auto; vertical-align: -3px; margin-right: 10px; }

/* The header bleeds to the viewport edges past the body's side padding. */
header.site { margin: 0 calc(50% - 50vw); padding: 22px calc(50vw - 50%) 14px; color: #ffffff;
  background: var(--header); border-bottom: 3px solid; border-image: var(--accent) 1; }
header.site h1 { font-size: 26px; line-height: 1.25; }
header.site h1 .logo { height: 30px; vertical-align: -4px; }
header.site .meta { color: #b9c8de; font-size: 12px; }
header.site a { color: #7ad6eb; }
header.site details.how > summary, header.site nav.sections { color: #b9c8de; }
header.site details.how > summary:hover { color: #ffffff; }
details.how { margin: 8px 0 6px; max-width: 95ch; }
details.how > summary { font-size: 13px; color: var(--muted); }
details.how > summary:hover { color: var(--fg); }
details.how ul { margin: 6px 0 4px; padding-left: 22px; font-size: 13px; }
details.how li { margin: 2px 0; }
.breadcrumb { font-size: 13px; margin: 0 0 8px; padding-top: 20px; }
nav.sections { font-size: 13px; color: var(--muted); margin: 8px 0 0; }
nav.sections a + a { margin-left: 14px; }

/* Tables. */
.wrap { overflow: auto; border-top: 1px solid var(--line); }
table { border-collapse: separate; border-spacing: 0; width: 100%; }
th, td { padding: 7px 12px; text-align: left; vertical-align: baseline; white-space: nowrap;
  border-bottom: 1px solid var(--line); }
thead th { color: var(--muted); font-size: 13px; font-weight: 600; border-bottom: 1px solid var(--line-strong);
  background: var(--bg); }
.wrap thead th { position: sticky; top: 0; z-index: 1; }
.num { text-align: right; font-variant-numeric: lining-nums tabular-nums; }
td.wrapping, th.wrapping { white-space: normal; }
table.reliability td.task { vertical-align: top; }
table.reliability td.task .chip { margin-top: 4px; }
table.plain { width: auto; }
table.plain th, table.plain td { padding: 5px 12px 5px 0; background: none; }
table.plain td + td, table.plain th + th { padding-left: 12px; }

.chip { display: inline-block; padding: 0 8px; border-radius: 999px; font-size: 12px; font-weight: 500; line-height: 20px;
  color: var(--muted); background: var(--stripe); border: 1px solid var(--line); white-space: nowrap; }
.chip.status-passed, .chip.pass { color: var(--pass-fg); background: var(--pass-bg); border-color: transparent; }
.chip.status-failed, .chip.status-timed-out, .chip.fail { color: var(--fail-fg); background: var(--fail-bg); border-color: transparent; }
.chip.status-non-result, .chip.status-incomplete, .chip.partial { color: var(--warn-fg); background: var(--warn-bg); border-color: transparent; }
.chip.class-weaviate-gap { color: var(--fail-fg); background: var(--fail-bg); border-color: transparent; }
.chip.class-agent-gap { color: var(--warn-fg); background: var(--warn-bg); border-color: transparent; }
.chip.class-scorer-bug, .chip.class-task-defect { color: var(--flag-fg); background: var(--flag-bg); border-color: transparent; }

/* Waffle grids: one cell per Trial, wrapping after ten so larger runs grow
   in rows of ten rather than one long strip. */
.waffle { display: inline-flex; flex-wrap: wrap; gap: 3px; max-width: calc(10 * 14px + 9 * 3px);
  vertical-align: middle; margin-right: 8px; }
.waffle.small { max-width: calc(10 * 10px + 9 * 3px); }
.waffle a { width: 14px; height: 14px; border-radius: 3px; background: var(--cell-none);
  box-shadow: inset 0 0 0 1px rgba(19, 12, 73, 0.12); }
.waffle a.status-passed { background: var(--cell-pass); }
.waffle a.status-failed, .waffle a.status-timed-out { background: var(--cell-fail); }
.waffle a.status-non-result, .waffle a.status-incomplete { background: var(--cell-warn); }
.waffle a:hover { outline: 2px solid var(--link); }
.waffle.small a { width: 10px; height: 10px; border-radius: 2px; }

/* Rate bars: the fill runs to the rate on a light track of the same hue. The
   count is always written beside the bar, so colour is never the only cue. */
.rate { position: relative; display: inline-block; width: 120px; height: 8px; border-radius: 4px;
  vertical-align: middle; margin-right: 10px; }
.rate .fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 4px; }
.rate.passed { background: var(--pass-bg); }
.rate.passed .fill { background: var(--cell-pass); }
.rate.failed { background: var(--fail-bg); }
.rate.failed .fill { background: var(--cell-fail); }
.pct { display: inline-block; min-width: 4ch; }

/* Cards hold an item's detail, such as an opened finding or comparison, with
   one label column width so the sections read alike. */
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
  padding: 0 18px 14px; margin: 0 0 16px; max-width: 130ch; overflow-x: auto;
  box-shadow: 0 1px 3px rgba(19, 12, 73, 0.08); }
.card > :first-child { margin-top: 12px; }
.card > pre.message { max-width: 110ch; margin-bottom: 0; }
/* Folded lists (findings, comparisons): one summary row per item in a shared
   grid, opening in place to an inset card. Columns line up across rows
   because every row and the column header use the list's --columns. */
.fold-list { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; margin: 0 0 16px;
  max-width: 130ch; box-shadow: 0 1px 3px rgba(19, 12, 73, 0.08); overflow: hidden; }
.fold-list.findings { --columns: 1em minmax(14em, 1.4fr) minmax(12em, 1fr) 15em 11em; }
.fold-list.comparisons { --columns: 1em minmax(14em, 1.2fr) minmax(12em, 1fr) 9em minmax(14em, 1.2fr); }
.fold-list > .columns, details.fold > summary { display: grid; align-items: center; gap: 12px;
  grid-template-columns: var(--columns); padding: 7px 14px; }
.fold-list > .columns { font-size: 12px; font-weight: 600; color: var(--muted); background: var(--band);
  border-bottom: 1px solid var(--line-strong); }
details.fold + details.fold { border-top: 1px solid var(--line); }
details.fold > summary { list-style: none; cursor: pointer; font-size: 13px; }
details.fold > summary::-webkit-details-marker { display: none; }
details.fold > summary::before { content: "\\25B8"; color: var(--muted); }
details.fold[open] > summary::before { content: "\\25BE"; }
details.fold > summary:hover, details.fold:target > summary { background: var(--stripe); }
details.fold[open] > summary { background: var(--band); border-bottom: 1px solid var(--line); }
details.fold .name { font-weight: 600; overflow-wrap: anywhere; }
details.fold .nowrap { white-space: nowrap; }
.card.inset { border: 0; border-radius: 0; box-shadow: none; margin: 0; max-width: none; }
@media (max-width: 700px) {
  .fold-list > .columns { display: none; }
  .fold-list.findings, .fold-list.comparisons { --columns: 1em 1fr 1fr; }
}
.card dl.facts { grid-template-columns: 14em minmax(0, 95ch); margin: 10px 0 4px; }
.card ul { margin: 0; padding-left: 18px; }
.card li + li { margin-top: 4px; }
/* The arms' outcome sits in an inset panel; its labels stay in the card's
   label column. */
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 6px 12px; margin: 8px 0;
  width: fit-content; max-width: 100%; box-sizing: border-box; }
.panel .failing-agents { color: var(--muted); font-size: 12px; margin-top: 2px; }
.panel table.by-agent { margin-top: 10px; border-top: 1px solid var(--line); }
.panel .unpaired { margin: 6px 0 2px; }
.card .panel dl.facts { grid-template-columns: calc(14em - 13px) max-content; margin: 2px 0; align-items: center; }
/* Inside a card, each judge's part opens with a pill and a rule above it. */
.part { border-top: 1px solid var(--line-strong); margin-top: 12px; padding-top: 10px; }
summary + .part { border-top: 0; padding-top: 4px; }
.part .who { font-size: 13px; }
.pill { display: inline-block; padding: 0 9px; border-radius: 999px; font-size: 11.5px; font-weight: 600;
  line-height: 20px; color: var(--pill-fg); background: var(--pill-bg); margin-right: 4px; }
/* Column gap moves into dd padding so each row's rule runs unbroken. */
.judgment dl.facts { margin: 8px 0 2px; gap: 6px 0; }
.judgment dl.facts > dd { padding-left: 16px; }
.judgment dl.facts > dt:not(:first-child), .judgment dl.facts > dt:not(:first-child) + dd {
  border-top: 1px solid var(--line); padding-top: 6px; }
.disputed { color: var(--warn-fg); font-size: 12px; white-space: nowrap; }
table.trials { font-size: 13px; width: 100%; margin-top: 4px; }
table.trials td.wrapping { min-width: 18ch; max-width: 50ch; }
table.arms { font-size: 12.5px; }
table.arms th, table.arms td { padding-top: 3px; padding-bottom: 3px; vertical-align: middle; }
table.arms th { font-weight: 400; }
table.arms thead th { font-weight: 600; }
table.arms tbody th { color: var(--muted); padding-right: 24px; }
table.arms tr.group th { color: var(--fg); font-weight: 600; padding-top: 10px; white-space: normal; }
table.arms tbody tr:last-child > * { border-bottom: 0; }
table.arms .waffle { margin-right: 0; }
.delta { display: inline-block; padding: 0 7px; border-radius: 999px; font-weight: 600; line-height: 19px;
  color: var(--muted); background: var(--stripe); }
.delta.better { color: var(--pass-fg); background: var(--pass-bg); }
.delta.worse { color: var(--fail-fg); background: var(--fail-bg); }
table.arms td.change .figures { display: block; color: var(--muted); font-size: 11.5px; line-height: 1.35; margin-top: 2px; }
/* A long Treatment name wraps at its hyphens instead of widening its column. */
table.arms thead th.arm-name { white-space: normal; width: 8em; }
@media (max-width: 600px) { .card dl.facts, .card .panel dl.facts { grid-template-columns: 1fr; } }

tr.detail > td { background: var(--stripe); padding: 4px 12px 14px 40px; border-bottom: 1px solid var(--line-strong);
  white-space: normal; }
td.files a + a, .links a + a { margin-left: 12px; }

details > summary { cursor: pointer; }
details.prompt { margin: 4px 0; }
details.prompt > summary { font-size: 13px; padding: 2px 0; }
.definition { display: grid; gap: 4px; max-width: 120ch; }
.definition pre.prompt { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px;
  font-size: 12.5px; max-height: 420px; overflow: auto; }
.error { color: var(--fail-fg); background: var(--fail-bg); border-radius: 6px; padding: 8px 12px; }
dl.facts { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; margin: 12px 0; font-size: 13px; }
dl.facts dt { color: var(--muted); }
dl.facts dd { margin: 0; }

/* Transcript. */
ol.steps { list-style: none; padding: 0; margin: 0; max-width: 130ch; }
li.step { border-left: 2px solid var(--line-strong); padding: 4px 0 10px 14px; margin-left: 4px; }
.step-head { margin-bottom: 4px; }
.step .preview { color: var(--muted); font-size: 13px; }
.chip.source-user { color: var(--link); background: var(--hover); border-color: transparent; }
pre.message { font-family: inherit; font-size: 14px; margin: 2px 0 6px; }

/* The final agent message, with its Markdown rendered. */
.final { max-width: 110ch; border-left: 3px solid; border-image: var(--accent) 1; padding: 4px 0 4px 14px; }
.final > :first-child { margin-top: 0; }
.final h3 { font-size: 14px; margin: 14px 0 4px; }
.final h4 { color: var(--fg); margin: 10px 0 2px; }
.final pre { background: var(--stripe); border-radius: 6px; padding: 8px 10px; margin: 6px 0; }
.final ul, .final ol { margin: 4px 0 8px; padding-left: 22px; }
.final li { margin: 2px 0; }
.tool-call { border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px; margin: 6px 0; background: var(--stripe); }
.tool-name { font-family: Menlo, ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12.5px; font-weight: 600; }
.tool-call pre.output { margin-top: 4px; padding: 6px 10px; background: var(--bg); border-radius: 6px; max-height: 480px; overflow: auto; }
li.step details > pre { margin: 2px 0 6px; padding: 6px 10px; background: var(--stripe); border-radius: 6px; }

/* JSON tree. */
.tree { font-family: Menlo, ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12.5px; line-height: 1.6; }
.tree .children { padding-left: 18px; border-left: 1px solid var(--line); margin-left: 4px; }
.tree summary { list-style: none; }
.tree summary::-webkit-details-marker { display: none; }
.tree summary::before { content: "\\25B8"; display: inline-block; width: 1em; color: var(--muted); }
.tree details[open] > summary::before { content: "\\25BE"; }
.tree .leaf { padding-left: 1em; }
.tree .key { color: var(--fg); font-weight: 600; }
.tree .key::after { content: ":"; font-weight: 400; color: var(--muted); margin-right: 6px; }
.tree .type { color: var(--muted); }
.tree .string { color: var(--pass-fg); }
.tree .number { color: var(--link); }
.tree .literal { color: var(--warn-fg); }
.tree pre.string { margin: 2px 0 4px; padding: 6px 10px; background: var(--stripe); border-radius: 6px; color: var(--fg); }
"""
