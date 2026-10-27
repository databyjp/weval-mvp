"""Stylesheet and script embedded in every report page.

Each page carries its own copy so it opens on its own from ``file://``.
"""

STYLE = """
/* Muted text keeps at least 4.5:1 contrast on --bg and --stripe in both themes. */
:root {
  --bg: #ffffff; --fg: #1f2328; --muted: #59636e; --line: #e6e8eb; --line-strong: #c9ced4;
  --stripe: #f6f8fa; --hover: #eaf1fb; --link: #0969da; --code-bg: rgba(129, 139, 152, 0.14);
  --bar-required: rgba(31, 136, 61, 0.22); --bar-preferred: rgba(89, 99, 110, 0.16);
  --pass-fg: #116329; --pass-bg: #dafbe1; --fail-fg: #a40e26; --fail-bg: #ffebe9;
  --warn-fg: #7d4e00; --warn-bg: #fff8c5;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117; --fg: #e6edf3; --muted: #9198a1; --line: #262c36; --line-strong: #3d444d;
    --stripe: #151b23; --hover: #1c2636; --link: #4493f8; --code-bg: rgba(101, 108, 118, 0.3);
    --bar-required: rgba(63, 185, 80, 0.28); --bar-preferred: rgba(145, 152, 161, 0.22);
    --pass-fg: #56d364; --pass-bg: rgba(46, 160, 67, 0.18); --fail-fg: #ff7b72; --fail-bg: rgba(248, 81, 73, 0.18);
    --warn-fg: #e3b341; --warn-bg: rgba(187, 128, 9, 0.2);
  }
}
body { background: var(--bg); color: var(--fg); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
  margin: 24px 10%; }
@media (max-width: 600px) { body { margin: 16px; } }
h1 { font-size: 20px; font-weight: 600; margin: 0; }
h2 { font-size: 15px; font-weight: 600; margin: 28px 0 8px; }
h3 { font-size: 13px; font-weight: 600; margin: 16px 0 6px; color: var(--muted); }
p { margin: 0 0 8px; }
.intro { color: var(--muted); font-size: 13px; max-width: 90ch; margin: 0 0 16px; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
.mono, code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12.5px; }
code { background: var(--code-bg); border-radius: 4px; padding: 0 4px; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; margin: 0; }
.secondary, .muted { color: var(--muted); }
.note { color: var(--muted); font-size: 12px; margin-left: 6px; }

/* Header and tabs. */
header.site { padding: 20px 0 12px; }
header.site h1 { font-size: 26px; line-height: 1.25; }
header.site .lede { font-size: 15px; max-width: 95ch; margin: 8px 0 6px; }
header.site .meta { color: var(--muted); font-size: 12px; }
nav.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--line-strong); margin: 12px 0 16px; }
nav.tabs a { padding: 8px 14px; color: var(--muted); font-weight: 500; border-bottom: 2px solid transparent;
  margin-bottom: -1px; }
nav.tabs a:hover { color: var(--fg); text-decoration: none; }
nav.tabs a[aria-current="page"] { color: var(--fg); border-bottom-color: var(--fg); }
nav.tabs .count { color: var(--muted); font-weight: 400; margin-left: 4px; font-variant-numeric: tabular-nums; }
.breadcrumb { font-size: 13px; margin-bottom: 8px; }

/* Tables. */
.wrap { overflow: auto; border-top: 1px solid var(--line); }
.wrap.tall { max-height: calc(100vh - 220px); }
table { border-collapse: separate; border-spacing: 0; width: 100%; }
th, td { padding: 7px 12px; text-align: left; vertical-align: baseline; white-space: nowrap;
  border-bottom: 1px solid var(--line); }
thead th { color: var(--muted); font-size: 13px; font-weight: 600; border-bottom: 1px solid var(--line-strong);
  background: var(--bg); }
.wrap thead th { position: sticky; top: 0; z-index: 1; }
.num { text-align: right; font-variant-numeric: lining-nums tabular-nums; }
.group { padding-left: 28px; }
td.wrapping, th.wrapping { white-space: normal; }
table.plain { width: auto; }
table.plain th, table.plain td { padding: 5px 12px 5px 0; }
table.plain td + td, table.plain th + th { padding-left: 12px; }

table.sortable > thead th { cursor: pointer; user-select: none; }
table.sortable > thead th:hover { color: var(--fg); }
/* A fixed-width slot keeps headers from shifting when the sort arrow appears. */
table.sortable > thead th::after { content: ""; display: inline-block; width: 1.1em; text-align: right; }
table.sortable > thead th:hover::after { content: "\\2195"; opacity: 0.5; }
table.sortable > thead th[data-dir="asc"]::after { content: "\\2191"; opacity: 1; }
table.sortable > thead th[data-dir="desc"]::after { content: "\\2193"; opacity: 1; }
table.sortable > thead th[data-dir] { color: var(--fg); }

table.rows > tbody:nth-of-type(even) > tr.row { background: var(--stripe); }
table.rows > tbody > tr.row:hover { background: var(--hover); }
button.row-toggle { font: inherit; font-weight: 500; color: var(--link); background: none; border: 0; padding: 0;
  cursor: pointer; text-align: left; }
button.row-toggle:hover { text-decoration: underline; }

/* Pass-fraction bar behind the count; --fraction and --bar are set per cell. */
td.bar { min-width: 56px; background-image: linear-gradient(to right, var(--bar) var(--fraction), transparent var(--fraction));
  background-repeat: no-repeat; background-size: calc(100% - 16px) calc(100% - 10px); background-position: center; }

button.toggle { font: inherit; font-variant-numeric: tabular-nums; color: var(--fg); background: transparent;
  border: 1px solid var(--line-strong); border-radius: 6px; padding: 0 8px; cursor: pointer; }
button.toggle:hover { border-color: var(--muted); }
button.toggle::before { content: "\\25B8"; display: inline-block; width: 1em; color: var(--muted); }
button.toggle[aria-expanded="true"]::before { content: "\\25BE"; }

a.middle-truncate { display: inline-flex; max-width: 300px; vertical-align: bottom; }
a.middle-truncate > span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
a.middle-truncate > span:last-child { flex-shrink: 0; }

tr.detail > td { background: var(--stripe); padding: 4px 12px 14px 40px; border-bottom: 1px solid var(--line-strong);
  white-space: normal; }
tr.detail table { width: auto; }
tr.detail th { font-size: 12px; padding: 6px 12px; background: transparent; }
tr.detail td { padding: 5px 12px; }
tr.detail tr:last-child td { border-bottom: none; }
td.files a + a, .links a + a { margin-left: 12px; }

.chip { display: inline-block; padding: 0 8px; border-radius: 999px; font-size: 12px; font-weight: 500; line-height: 20px;
  color: var(--muted); background: var(--line); white-space: nowrap; }
.chip.status-passed, .chip.pass { color: var(--pass-fg); background: var(--pass-bg); }
.chip.status-failed, .chip.status-timed-out, .chip.fail { color: var(--fail-fg); background: var(--fail-bg); }
.chip.status-non-result, .chip.status-incomplete, .chip.partial { color: var(--warn-fg); background: var(--warn-bg); }
.check-ids { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; white-space: normal; }
.check-ids .failed-required { color: var(--fail-fg); }
.check-ids .failed-preferred { color: var(--muted); }
.check-ids span + span::before { content: ", "; color: var(--muted); }

/* Results filters. */
.filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; margin: 0 0 12px; font-size: 13px; }
.filters label { color: var(--muted); }
.filters select { font: inherit; color: var(--fg); background: var(--bg); border: 1px solid var(--line-strong);
  border-radius: 6px; padding: 2px 6px; margin-left: 6px; max-width: 280px; }
.filters .shown { color: var(--muted); font-variant-numeric: tabular-nums; }

/* Task catalog: one row per prompt variant, one column per Agent. */
#catalog td.task { white-space: normal; min-width: 240px; max-width: 46ch; }
#catalog td.task .name { font-weight: 600; }
#catalog td.task .motivation { color: var(--muted); font-size: 13px; margin: 2px 0 6px; }
#catalog td.result { min-width: 120px; max-width: 220px; white-space: normal; }
#catalog td.result a.chip { text-decoration: none; }
#catalog td.result .check-ids { display: block; margin-top: 2px; }
#catalog tbody + tbody > tr:first-child > td { border-top: 1px solid var(--line-strong); }
#catalog th.agent { white-space: normal; min-width: 110px; }
#catalog tfoot th, #catalog tfoot td { border-top: 1px solid var(--line-strong); border-bottom: none; font-weight: 600; }
#catalog tfoot th { color: var(--muted); font-size: 13px; text-align: right; }
#catalog tfoot td.num { text-align: left; font-variant-numeric: tabular-nums; }
.definition { display: grid; gap: 4px; max-width: 120ch; }
.definition pre.prompt { background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px;
  font-size: 12.5px; max-height: 420px; overflow: auto; }
details > summary { cursor: pointer; }
details.prompt { margin: 4px 0; }
details.prompt > summary { font-size: 13px; padding: 2px 0; }
.error { color: var(--fail-fg); background: var(--fail-bg); border-radius: 6px; padding: 8px 12px; }
dl.facts { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; margin: 12px 0; font-size: 13px; }
dl.facts dt { color: var(--muted); }
dl.facts dd { margin: 0; }
section[hidden] { display: none; }

/* Transcript. */
ol.steps { list-style: none; padding: 0; margin: 0; max-width: 130ch; }
li.step { border-left: 2px solid var(--line-strong); padding: 4px 0 10px 14px; margin-left: 4px; }
.step-head { margin-bottom: 4px; }
.chip.source-user { color: var(--link); background: var(--hover); }
pre.message { font-family: inherit; font-size: 14px; margin: 2px 0 6px; }
pre.message.final { max-width: 110ch; border-left: 3px solid var(--line-strong); padding: 4px 0 4px 12px; }
.tool-call { border: 1px solid var(--line); border-radius: 6px; padding: 6px 10px; margin: 6px 0; background: var(--stripe); }
.tool-name { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12.5px; font-weight: 600; }
.tool-call pre.output { margin-top: 4px; padding: 6px 10px; background: var(--bg); border-radius: 6px; max-height: 480px; overflow: auto; }
li.step details > pre { margin: 2px 0 6px; padding: 6px 10px; background: var(--stripe); border-radius: 6px; }

/* JSON tree. */
.tree { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12.5px; line-height: 1.6; }
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

INDEX_SCRIPT = """
// State lives in the URL hash, e.g. #tab=results&task=tasks/x/y&agent=z, so views can be linked.
const FILTERS = ["task", "variant", "agent", "treatment"];
const runs = document.getElementById("runs");

function readHash() {
  const state = new URLSearchParams(location.hash.slice(1));
  return { tab: state.get("tab") || "tasks", ...Object.fromEntries(FILTERS.map(k => [k, state.get(k) || ""])) };
}

function writeHash(state) {
  const params = new URLSearchParams({ tab: state.tab });
  FILTERS.forEach(k => { if (state[k]) params.set(k, state[k]); });
  // location.replace, unlike history.replaceState, may change the hash of a file:// page.
  location.replace("#" + params.toString().replaceAll("%2F", "/"));
}

function show(state) {
  document.querySelectorAll("section.tab").forEach(s => { s.hidden = s.id !== state.tab; });
  document.querySelectorAll("nav.tabs a").forEach(a => {
    if (a.dataset.tab === state.tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  FILTERS.forEach(k => { document.getElementById("filter-" + k).value = state[k]; });
  let shown = 0;
  [...runs.tBodies].forEach(body => {
    const match = FILTERS.every(k => !state[k] || body.dataset[k] === state[k]);
    body.hidden = !match;
    shown += match;
  });
  document.getElementById("shown").textContent = `Showing ${shown} of ${runs.tBodies.length} runs`;
  if (state.tab === "tasks" && state.task) {
    const body = document.getElementById("task-" + state.task);
    if (body) { expand(body, true); body.scrollIntoView({ block: "start" }); }
  }
}

function expand(body, open) {
  body.querySelector("tr.detail").hidden = !open;
  body.querySelectorAll("button[aria-expanded]").forEach(b => b.setAttribute("aria-expanded", String(open)));
}

document.querySelectorAll("button.toggle, button.row-toggle").forEach(button => button.addEventListener("click", () => {
  const body = button.closest("tbody");
  expand(body, body.querySelector("tr.detail").hidden);
}));

FILTERS.forEach(k => document.getElementById("filter-" + k).addEventListener("change", event => {
  const state = { ...readHash(), tab: "results", [k]: event.target.value };
  writeHash(state);
  show(state);
}));
document.getElementById("clear-filters").addEventListener("click", event => {
  event.preventDefault();
  const state = { tab: "results", ...Object.fromEntries(FILTERS.map(k => [k, ""])) };
  writeHash(state);
  show(state);
});
window.addEventListener("hashchange", () => show(readHash()));
show(readHash());

runs.querySelectorAll("thead th").forEach((th, column) => th.addEventListener("click", () => {
  const dir = th.dataset.dir === "asc" ? "desc" : "asc";
  runs.querySelectorAll("thead th").forEach(other => delete other.dataset.dir);
  th.dataset.dir = dir;
  const numeric = th.dataset.type === "num";
  const key = body => body.querySelector("tr.row").children[column].dataset.sort;
  const bodies = [...runs.tBodies];
  bodies.sort((a, b) => {
    const x = key(a), y = key(b);
    if (x === "" || y === "") return (x === "") - (y === "");  // blanks last either way
    const order = numeric ? x - y : x.localeCompare(y);
    return dir === "asc" ? order : -order;
  });
  bodies.forEach(body => runs.appendChild(body));
}));
"""
