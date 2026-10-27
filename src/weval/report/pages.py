"""Render the report's HTML pages from collected report data.

The index has a Tasks tab (the catalog, with each Agent's latest baseline
result per prompt variant, and the Agents), a Results tab (one row per run),
and a Treatments tab (each Treatment's runs beside the baseline runs of the
same Task, prompt variant, and Agent). Each Trial also gets its own page with
its checks, usage, prompt, and snapshot.
All links are relative, so the pages work from ``file://``.
"""

import json
import os
import re
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

from weval import analysis
from weval.diagnostics import diagnose
from weval.labels import label
from weval.report.assets import INDEX_SCRIPT, STYLE
from weval.report.collect import (
    Comparison, RunSummary, TaskDefinition, TrialSummary, compare_treatments, fisher_exact, mean_usage, wilson_interval,
)

# Filter value and label for runs without a Treatment.
BASELINE = "baseline"
# A JSON array longer than this shows its first items and points to the raw file.
LIST_LIMIT = 50
# Transcript tool output beyond this many characters is left to trajectory.json.
OUTPUT_LIMIT = 6000


def render_index(
    runs: list[RunSummary],
    tasks: list[TaskDefinition],
    agents: dict[str, dict],
    *,
    index_dir: Path,
    trial_pages: dict[Path, Path],
    generated: datetime,
) -> str:
    """Return ``index.html``. ``trial_pages`` maps each Trial directory to its
    page; links are relative to ``index_dir``."""
    links = _Links(index_dir)
    agent_names = _agents_with_runs(runs, agents)
    trial_count = sum(len(run.trials) for run in runs)
    variant_count = sum(len(task.prompts) for task in tasks)
    comparisons = compare_treatments(runs)
    return _page(
        "Weaviate AX Evaluation",
        f"""
<header class="site"><h1>Weaviate Agent Experience (AX) Evaluation</h1>
<p class="lede">Each Task gives a coding agent a Weaviate job in a live environment, and a verifier scores
the result against required and preferred checks. Tasks shows what each Task asks and how each Agent did on
its latest baseline run; Results lists every run and its Trials; Treatments sets each Treatment's runs beside
the baseline runs of the same Task, prompt variant, and Agent.</p>
<span class="meta">{len(tasks)} Tasks, {variant_count} prompt variants, {len(agents)} Agents, {len(runs)} runs,
{trial_count} Trials. Generated {generated:%Y-%m-%d %H:%M}.</span></header>
<nav class="tabs">
<a href="#tab=tasks" data-tab="tasks">Tasks<span class="count">{len(tasks)}</span></a>
<a href="#tab=results" data-tab="results">Results<span class="count">{len(runs)}</span></a>
<a href="#tab=treatments" data-tab="treatments">Treatments<span class="count">{len(comparisons)}</span></a>
</nav>
<section class="tab" id="tasks">{_tasks_tab(tasks, runs, agents, agent_names, links)}</section>
<section class="tab" id="results" hidden>{_results_tab(runs, agents, links, trial_pages)}</section>
<section class="tab" id="treatments" hidden>{_treatments_tab(comparisons, tasks, index_dir, links)}</section>
<script>{INDEX_SCRIPT}</script>""",
    )


def render_trial(
    run: RunSummary, trial: TrialSummary, *, page_dir: Path, index: Path, expected: dict | None = None,
) -> str:
    """Return one Trial's page; links are relative to ``page_dir``.
    ``expected`` is the Task's ``EXPECTED``, for the checks' diagnostics."""
    links = _Links(page_dir)
    record = trial.record or {}
    agent = record.get("agent") or {}
    usage = record.get("usage") or {}
    task_link = links.index(index, tab="tasks", task=run.task)
    results_link = links.index(index, tab="results", task=run.task, variant=run.prompt_variant, agent=run.agent)

    facts = [
        ("Status", f'<span class="chip status-{escape(trial.status)}">{escape(trial.status)}</span>'
                   + (f' <span class="note">reward {record["reward"]}</span>' if record.get("reward") is not None else "")),
        ("Task", f'<a href="{task_link}">{escape(_task_name(run.task))}</a>'),
        ("Prompt variant", escape(run.prompt_variant)),
        ("Agent", escape(run.agent) + (f' <span class="note">{escape(_agent_spec(agent))}</span>' if agent else "")),
        ("Date", run.date.strftime("%Y-%m-%d %H:%M") if run.date else ""),
        ("Environment", escape(run.environment)),
        ("Run", links.link(run.path, run.path.name, css="mono")),
        ("Trial", links.link(trial.path, trial.path.name, css="mono")),
    ]
    if record.get("exception"):
        facts.append(("Exception", f'<span class="mono">{escape(str(record["exception"]))}</span>'))
    if record.get("error_stage"):
        facts.append(("Error stage", escape(str(record["error_stage"]))))
    if record.get("missing_logs"):
        facts.append(("Missing logs", ", ".join(f"<code>{escape(str(m))}</code>" for m in record["missing_logs"])))

    checks = _read_json(trial.path / "verifier/checks.json") or record.get("checks") or []
    snapshot_file = trial.path / "verifier/snapshot.json"
    snapshot = _read_json(snapshot_file)
    prompt_file = run.path / "task/instruction.md"
    found = diagnose(trial.path, expected or {}, snapshot or {}, checks)
    # Saved labels only: building the report never calls Jev.
    labelled = label(trial.path, checks, call=False)["labels"]

    sections = [
        (f'<div class="breadcrumb"><a href="{results_link}">&larr; Results</a>'
         f' <span class="muted">/ {escape(run.path.name)}</span></div>'),
        f"<h1>{escape(_task_name(run.task))} <span class=\"muted\">with</span> {escape(run.agent)}</h1>",
        "<dl class=\"facts\">" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts) + "</dl>",
        _final_message(trial.path / "agent/trajectory.json"),
        "<h2>Checks</h2>" + (_checks_table(checks, found, labelled) if checks else '<p class="muted">No checks recorded.</p>')
        + _diagnostics(found),
        "<h2>Usage</h2>" + _usage(trial, usage),
        "<h2>Files</h2>" + '<p class="links">'
        + "".join(links.link(path, label) for label, path in trial.files.items()) + "</p>",
    ]
    trajectory = _read_json(trial.path / "agent/trajectory.json")
    if trajectory:
        sections.append(
            "<h2>Transcript</h2>"
            f'<p class="intro">Harbor\'s trajectory, step by step. Raw file: '
            f'{links.link(trial.path / "agent/trajectory.json", "trajectory.json")}.</p>'
            + _transcript(trajectory["steps"])
        )
    elif prompt_file.is_file():
        sections.append(
            '<h2>Prompt</h2><p class="intro">As packaged for this run, including the shared Trial-environment notes.</p>'
            f'<details class="prompt"><summary>{links.link(prompt_file, "task/instruction.md")}</summary>'
            f'<div class="definition"><pre class="prompt">{escape(prompt_file.read_text())}</pre></div></details>'
        )
    if snapshot is not None:
        sections.append(
            "<h2>Snapshot</h2>"
            f'<p class="intro">The live state the verifier captured. Raw file: {links.link(snapshot_file, "snapshot.json")}.</p>'
            f'<div class="tree">{_tree_children(snapshot, open_depth=1)}</div>'
        )
    if trial.record:
        sections.append(
            f"<h2>weval.json</h2><details><summary class=\"muted\">All fields</summary>"
            f'<div class="tree">{_tree_children(trial.record, open_depth=0)}</div></details>'
        )
    return _page(f"{_task_name(run.task)} with {run.agent}", "\n".join(sections))


# --- Tasks tab ---------------------------------------------------------------


def _tasks_tab(
    tasks: list[TaskDefinition], runs: list[RunSummary], agents: dict[str, dict],
    agent_names: list[str], links: "_Links",
) -> str:
    # Runs are newest first, so the first run per key is the latest. Treatment
    # runs are left to the Treatments tab, so a cell is always a baseline result.
    latest: dict[tuple[str, str, str], RunSummary] = {}
    run_counts: Counter = Counter()
    for run in runs:
        if run.treatment:
            continue
        key = (run.task, run.prompt_variant, run.agent)
        latest.setdefault(key, run)
        run_counts[key] += 1

    # Per Agent: prompt variants whose latest run passed in every scored Trial, of those run.
    totals = []
    for name in agent_names:
        latest_runs = [latest[(task.path, v, name)] for task in tasks for v in task.prompts
                       if (task.path, v, name) in latest]
        all_passed = sum(bool(r.scored) and all(t.status == "passed" for t in r.scored) for r in latest_runs)
        totals.append(f'<td class="num">{all_passed}/{len(latest_runs)}</td>' if latest_runs else "<td></td>")
    agent_headers = "".join(
        f'<th class="agent" title="{escape(_agent_spec(agents.get(name, {})))}">{escape(name)}</th>'
        for name in agent_names
    )
    bodies = []
    for task in tasks:
        rows = []
        for i, prompt_variant in enumerate(task.prompts):
            checks = task.checks_for(prompt_variant)
            required = sum(c.required for c in checks)
            cells = "".join(
                _latest_cell(latest.get((task.path, prompt_variant, name)),
                             run_counts[(task.path, prompt_variant, name)], links)
                for name in agent_names
            )
            task_cell = ""
            if i == 0:
                task_cell = (
                    f'<td class="task" rowspan="{len(task.prompts)}">'
                    f'<div class="name">{escape(_task_name(task.path))}</div>'
                    f'<div class="motivation">{_inline_markdown(task.motivation)}</div>'
                    '<button class="toggle" aria-expanded="false">definition</button></td>'
                )
            checks_cell = (
                '<span class="chip fail">check.py error</span>' if task.check_error
                else f"{required} required, {len(checks) - required} preferred"
            )
            rows.append(
                f'<tr class="variant">{task_cell}<td class="mono">{escape(prompt_variant)}</td>'
                f'<td class="secondary">{checks_cell}</td>{cells}</tr>'
            )
        bodies.append(
            f'<tbody id="task-{escape(task.path)}">{"".join(rows)}'
            f'<tr class="detail" hidden><td colspan="{3 + len(agent_names)}">{_definition(task, links)}</td></tr></tbody>'
        )

    agent_rows = []
    for name, spec in agents.items():
        others = ", ".join(f"{k} = {v}" for k, v in spec.items() if k not in ("harness", "version", "model"))
        count = sum(run.agent == name for run in runs)
        runs_link = f'<a href="{links.index(None, tab="results", agent=name)}">{count}</a>' if count else "0"
        agent_rows.append(
            f'<tr><td class="mono">{escape(name)}</td><td>{escape(spec.get("harness", ""))}</td>'
            f'<td class="mono">{escape(spec.get("version", ""))}</td><td class="mono">{escape(spec.get("model", ""))}</td>'
            f'<td class="secondary">{escape(others)}</td><td class="num">{runs_link}</td></tr>'
        )

    return f"""
<div class="wrap"><table id="catalog">
<thead><tr><th>Task</th><th>Prompt variant</th><th>Checks</th>{agent_headers}</tr></thead>
{"".join(bodies)}
<tfoot><tr><th colspan="3">Prompt variants whose latest baseline run passed every scored Trial</th>{"".join(totals)}</tr></tfoot>
</table></div>
<h2>Agents</h2>
<p class="intro">Named Agents in <code>agents.toml</code>.</p>
<table class="plain">
<thead><tr><th>Agent</th><th>Harness</th><th>Version</th><th>Model</th><th>Other settings</th><th class="num">Runs</th></tr></thead>
<tbody>{"".join(agent_rows)}</tbody>
</table>"""


def _latest_cell(run: RunSummary | None, run_count: int, links: "_Links") -> str:
    if run is None:
        return '<td class="result"><span class="muted">&middot;</span></td>'
    scored = run.scored
    passed = sum(t.status == "passed" for t in scored)
    if not scored:
        label, css = Counter(t.status for t in run.trials).most_common(1)[0][0], "partial"
    else:
        label = f"{passed}/{len(scored)}"
        css = "pass" if passed == len(scored) else "fail" if passed == 0 else "partial"
    failed = Counter(check for t in scored for check in t.failed_required)
    title = (f"Latest baseline run {run.date:%Y-%m-%d %H:%M}, " if run.date else "Latest baseline run, ") + (
        f"{passed} of {len(scored)} scored Trials passed" if scored else "no scored Trials"
    )
    href = links.index(None, tab="results", task=run.task, variant=run.prompt_variant, agent=run.agent,
                       treatment=BASELINE)
    # Earlier runs may have used an older Task version, so they are counted, not scored.
    earlier = f'<span class="note">+{run_count - 1} earlier</span>' if run_count > 1 else ""
    return (
        f'<td class="result"><a class="chip {css}" href="{href}" title="{escape(title)}">{escape(label)}</a>{earlier}'
        + (f'<span class="check-ids">{_check_ids(failed, "failed-required")}</span>' if failed else "")
        + "</td>"
    )


def _definition(task: TaskDefinition, links: "_Links") -> str:
    config = task.config
    settings = [
        ("Agent timeout", _format_duration((config.get("agent") or {}).get("timeout_sec"))),
        ("Verifier timeout", _format_duration((config.get("verifier") or {}).get("timeout_sec"))),
        ("Build timeout", _format_duration((config.get("environment") or {}).get("build_timeout_sec"))),
        ("Verifier env", ", ".join(f"<code>{escape(k)}={escape(str(v))}</code>"
                                   for k, v in ((config.get("verifier") or {}).get("env") or {}).items())),
    ]
    files = [(task.page, "Task page")] + [
        (task.directory / rel, rel) for rel in
        ("instruction.md", "check.py", "snapshot.py", "solution/solve.sh", "environment", "task.toml")
    ]
    parts = []
    if task.summary:
        parts.append(f"<p>{_inline_markdown(task.summary)}</p>")
    parts.append('<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in settings if v) + "</dl>")
    parts.append('<p class="links">' + "".join(
        links.link(path, label) for path, label in files if path and path.exists()) + "</p>")

    parts.append("<h3>Checks</h3>")
    if task.check_error:
        parts.append(f'<pre class="error">{escape(task.check_error)}</pre>')
    elif task.checks:
        rows = "".join(
            f'<tr><td class="mono">{escape(c.id)}</td>'
            f'<td><span class="chip">{"required" if c.required else "preferred"}</span></td>'
            f'<td class="mono secondary">{escape(c.prompt_variant or "all")}</td>'
            f'<td class="wrapping">{_inline_markdown(c.description)}</td></tr>'
            for c in sorted(task.checks, key=lambda c: (c.prompt_variant is not None, not c.required))
        )
        parts.append('<table><thead><tr><th>Check</th><th>Tier</th><th>Prompt variant</th><th>Description</th>'
                     f"</tr></thead><tbody>{rows}</tbody></table>")
    else:
        parts.append('<p class="muted">No checks.</p>')

    parts.append("<h3>Prompts</h3>")
    for i, (prompt_variant, prompt) in enumerate(task.prompts.items()):
        source = "instruction.md" if prompt_variant == "default" else f"prompts/{prompt_variant}.md"
        parts.append(
            f'<details class="prompt"{" open" if i == 0 else ""}><summary><span class="mono">{escape(prompt_variant)}</span>'
            f' <span class="muted">{escape(source)}</span></summary><pre class="prompt">{escape(prompt)}</pre></details>'
        )
    return f'<div class="definition">{"".join(parts)}</div>'


# --- Results tab -------------------------------------------------------------


def _results_tab(
    runs: list[RunSummary], agents: dict[str, dict], links: "_Links", trial_pages: dict[Path, Path],
) -> str:
    # Classes: "num" right-aligns with tabular figures, "secondary" mutes, and
    # "group" opens a column group (identity, outcome, effort, links) with extra space.
    columns = [
        ("Task", "text", ""), ("Prompt variant", "text", ""), ("Treatment", "text", ""),
        ("Agent", "text", ""), ("Date", "text", "secondary"), ("Environment", "text", "secondary"),
        ("Required", "num", "num group bar"), ("Preferred", "num", "num bar"),
        ("Failed required checks", "text", "check-ids"),
        ("Cost (USD)", "num", "num group"), ("Tokens (k)", "num", "num"), ("Turns", "num", "num"),
        ("Duration", "num", "num"), ("Trials", "num", "group"), ("Output", "text", ""),
    ]
    header = "".join(f'<th data-type="{kind}" class="{css}">{name}</th>' for name, kind, css in columns)
    bodies = []
    for run in runs:
        scored = run.scored
        passed = sum(t.status == "passed" for t in scored)
        with_preferred = [t for t in scored if t.preferred_passed is not None]
        preferred_passed = sum(t.preferred_passed for t in with_preferred)
        failed = Counter(check for t in scored for check in t.failed_required)
        unscored = len(run.trials) - len(scored)
        cost, tokens, turns, duration = (run.mean(a) for a in ("cost_usd", "tokens", "turns", "duration_s"))
        # The run name repeats the Task and Agent columns; truncating its middle
        # keeps the timestamp and Agent visible, and the title shows it whole.
        head, separator, tail = run.path.name.rpartition("__")
        output = (
            f'<a class="middle-truncate mono" href="{links.href(run.path)}" title="{escape(run.path.name)}">'
            f"<span>{escape(head + separator)}</span><span>{escape(tail)}</span></a>"
        )
        cells = [
            (f'<button class="row-toggle" aria-expanded="false">{escape(_task_name(run.task))}</button>', run.task),
            (escape(run.prompt_variant), run.prompt_variant),
            (escape(run.treatment) if run.treatment else f'<span class="muted">{BASELINE}</span>', run.treatment),
            (f'<span title="{escape(_agent_spec(agents.get(run.agent, {})))}">{escape(run.agent)}</span>', run.agent),
            (run.date.strftime("%Y-%m-%d %H:%M") if run.date else "", run.date.isoformat() if run.date else ""),
            (escape(run.environment), run.environment),
            _fraction(passed, len(scored), "--bar-required"),
            _fraction(preferred_passed, len(with_preferred), "--bar-preferred"),
            (_check_ids(failed, "failed-required"), " ".join(sorted(failed))),
            (_format_cost(cost), cost),
            (_format_tokens(tokens), tokens),
            (f"{turns:.0f}" if turns is not None else "", turns),
            (_format_duration(duration), duration),
            (f'<button class="toggle" aria-expanded="false">{len(run.trials)}</button>'
             + (f' <span class="note">+{unscored} unscored</span>' if unscored else ""), len(run.trials)),
            (output, run.path.name),
        ]
        row = "".join(_cell(*cell, css=css) for cell, (_, _, css) in zip(cells, columns))
        trial_rows = "".join(
            "<tr>"
            f'<td class="mono">{links.link(trial_pages[t.path], t.path.name)}</td>'
            f'<td><span class="chip status-{escape(t.status)}">{escape(t.status)}</span></td>'
            f'<td class="check-ids">{_check_ids(Counter(t.failed_required), "failed-required")}'
            f'{_check_ids(Counter(t.failed_preferred), "failed-preferred")}</td>'
            f'<td class="num">{_format_cost(t.cost_usd)}</td>'
            f'<td class="num">{_format_tokens(t.tokens)}</td>'
            f"<td class=\"num\">{'' if t.turns is None else t.turns}</td>"
            f'<td class="num">{_format_duration(t.duration_s)}</td>'
            f"<td class=\"files\">{''.join(links.link(path, label) for label, path in t.files.items())}</td>"
            "</tr>"
            for t in run.trials
        )
        data = (f'data-task="{escape(run.task)}" data-variant="{escape(run.prompt_variant)}" '
                f'data-agent="{escape(run.agent)}" data-treatment="{escape(run.treatment or BASELINE)}"')
        bodies.append(
            f'<tbody {data}><tr class="row">{row}</tr>'
            f'<tr class="detail" hidden><td colspan="{len(columns)}"><table>'
            '<tr><th>Trial</th><th>Status</th><th>Failed checks</th><th class="num">Cost (USD)</th>'
            '<th class="num">Tokens (k)</th><th class="num">Turns</th><th class="num">Duration</th>'
            "<th>Files</th></tr>"
            f"{trial_rows}</table></td></tr></tbody>"
        )

    def select(key: str, label: str, values: list[str], display=lambda v: v) -> str:
        options = "".join(f'<option value="{escape(v)}">{escape(display(v))}</option>' for v in values)
        return f'<label>{label}<select id="filter-{key}"><option value="">All</option>{options}</select></label>'

    filters = (
        select("task", "Task", sorted({r.task for r in runs if r.task}), _task_name)
        + select("variant", "Prompt variant", sorted({r.prompt_variant for r in runs if r.prompt_variant}))
        + select("agent", "Agent", sorted({r.agent for r in runs if r.agent}))
        + select("treatment", "Treatment", [BASELINE] + sorted({r.treatment for r in runs if r.treatment}))
        + '<a href="#tab=results" id="clear-filters">Clear</a><span class="shown" id="shown"></span>'
    )
    return f"""
<div class="filters">{filters}</div>
<div class="wrap tall"><table id="runs" class="sortable rows">
<thead><tr>{header}</tr></thead>
{"".join(bodies)}
</table></div>"""


# --- Treatments tab ----------------------------------------------------------


def _treatments_tab(
    comparisons: list[Comparison], tasks: list[TaskDefinition], outputs_dir: Path, links: "_Links",
) -> str:
    if not comparisons:
        return '<p class="muted">No Treatment runs are retained.</p>'
    columns = [
        ("Treatment", ""), ("Task", ""), ("Prompt variant", ""), ("Agent", ""), ("Arm", "group"),
        ("Runs", "num"), ("Required", "num group bar"), ("Failed required checks", "check-ids"),
        ("Cost (USD)", "num group"), ("Tokens (k)", "num"), ("Uncached input (k)", "num"), ("Turns", "num"),
        ("Duration", "num"),
    ]
    header = "".join(f'<th class="{css}">{name}</th>' for name, css in columns)
    expected = {task.path: task.expected for task in tasks}
    bodies = []
    for comparison in comparisons:
        arms = [(BASELINE, comparison.baseline), (comparison.treatment, comparison.treated)]
        baseline_trials = [t for run in comparison.baseline for t in run.trials]
        baseline_scored = [t for run in comparison.baseline for t in run.scored]
        baseline_passed = sum(t.status == "passed" for t in baseline_scored)
        rows = []
        for i, (arm, arm_runs) in enumerate(arms):
            trials = [t for run in arm_runs for t in run.trials]
            scored = [t for run in arm_runs for t in run.scored]
            passed = sum(t.status == "passed" for t in scored)
            failed = Counter(check for t in scored for check in t.failed_required)
            href = links.index(None, tab="results", task=comparison.task, variant=comparison.prompt_variant,
                               agent=comparison.agent, treatment=arm)
            runs_cell = (f'<a href="{href}">{len(arm_runs)}</a> <span class="note">{len(trials)} Trial{"" if len(trials) == 1 else "s"}</span>'
                         if arm_runs else '<span class="muted">none</span>')
            # The Treatment row notes each usage mean's change from the baseline.
            reference = baseline_trials if i else None
            identity = "" if i else "".join(f'<td rowspan="2">{value}</td>' for value in (
                escape(comparison.treatment) + _version_note(comparison.treatment_version),
                escape(_task_name(comparison.task)) + _version_note(comparison.task_version, comparison.check_version),
                escape(comparison.prompt_variant), escape(comparison.agent)))
            required = _fraction(passed, len(scored), "--bar-required")
            if scored:
                low, high = wilson_interval(passed, len(scored))
                note = f"{100 * low:.0f}–{100 * high:.0f}%"
                if i and baseline_scored:
                    note += f" · p {fisher_exact(passed, len(scored), baseline_passed, len(baseline_scored)):.2g}"
                required = (required[0] + f' <span class="note">{note}</span>', *required[1:])
            cells = [
                (escape(arm), ""), (runs_cell, len(arm_runs)),
                required,
                (_check_ids(failed, "failed-required"), ""),
                _usage_mean(trials, reference, "cost_usd", _format_cost),
                _usage_mean(trials, reference, "tokens", _format_tokens),
                _usage_mean(trials, reference, "uncached_input", _format_tokens),
                _usage_mean(trials, reference, "turns", lambda v: "" if v is None else f"{v:.0f}"),
                _usage_mean(trials, reference, "duration_s", _format_duration),
            ]
            rows.append('<tr class="row">' + identity + "".join(
                _cell(*cell, css=css) for cell, (_, css) in zip(cells, columns[4:])) + "</tr>")
        # Saved analyses only: building the report never calls the analyst.
        found = analysis.analyse(comparison, expected.get(comparison.task, {}), outputs_dir, call=False)
        rows.append(f'<tr><td colspan="{len(columns)}" class="wrapping">{_analysis(found)}</td></tr>')
        bodies.append(f"<tbody>{''.join(rows)}</tbody>")
    return f"""
<p class="intro">Each Treatment version's runs beside the baseline runs of the same Task, prompt variant, and Agent
that ran the same Task and check versions (fingerprints in <code>weval.json</code>). Runs recorded without
fingerprints are compared only with each other. Under each pass rate is its 95% Wilson interval; the Treatment
row adds the two-sided Fisher's exact p-value against the baseline. Usage is the mean per Trial; uncached input
leaves out prompt-cache reads. The Treatment row notes each mean's change from the baseline. Under each pair is
its saved LLM analysis (<code>weval analyse</code>), checked against the facts it was given, and where a hand-coded
rule proposes another class for the same failed check.</p>
<div class="wrap"><table id="treatments-table" class="rows">
<thead><tr>{header}</tr></thead>
{"".join(bodies)}
</table></div>"""


def _analysis(found: dict) -> str:
    """A comparison's saved analysis from ``weval.analysis.analyse``, with
    the rule's disagreements and proposals, folded under its result."""
    answer = found["analysis"]
    if answer:
        summary = f'Analysis <span class="note">{escape(str(found["model"]))}</span> {escape(answer["result"])}'
    elif found["problems"]:
        summary = '<span class="muted">Analysis rejected:</span> ' + escape("; ".join(found["problems"]))
    else:
        summary = f'<span class="muted">{escape(found["note"] or "not analysed")}</span>'
    parts = []
    for pattern in (answer or {}).get("patterns", []):
        parts.append(
            f'<li><span class="chip">{escape(pattern["class"])}</span> {escape(pattern["summary"])}'
            f'<br><span class="note">{", ".join(f"<code>{escape(c)}</code>" for c in pattern["checks"])} in '
            f'{", ".join(f"<code>{escape(t)}</code>" for t in pattern["trials"])}</span>'
            f'<br>{escape(pattern["evidence"])}<br><span class="muted">{escape(pattern["reason"])}</span></li>')
    sections = [f"<h3>Failure patterns</h3><ul>{''.join(parts)}</ul>"] if parts else []
    if found["disagreements"]:
        sections.append("<h3>Rule disagreements</h3><ul>" + "".join(
            f'<li><code>{escape(d["trial"])}</code> <code>{escape(d["check"])}</code>: analyst '
            f'{escape(d["analyst"])}, rule {escape(d["class"])} ({escape(d["reason"])})</li>'
            for d in found["disagreements"]) + "</ul>")
    for title, key in (("Caveats", "caveats"), ("Open questions", "open_questions")):
        if (answer or {}).get(key):
            sections.append(f"<h3>{title}</h3><ul>" + "".join(f"<li>{escape(i)}</li>" for i in answer[key]) + "</ul>")
    if found["rule"]:
        sections.append("<h3>Rule proposals</h3><ul>" + "".join(
            f'<li><code>{escape(r["trial"])}</code> <code>{escape(r["check"])}</code>: {escape(r["class"])} '
            f'<span class="muted">({escape(r["reason"])})</span></li>' for r in found["rule"]) + "</ul>")
    return f"<details><summary>{summary}</summary>{''.join(sections)}</details>"


def _version_note(*versions: str | None) -> str:
    """Short fingerprints as a note under a Treatments-tab cell, or "unversioned"."""
    if not any(versions):
        return ' <span class="note">unversioned</span>'
    return f' <span class="note mono">{" · ".join(escape(v[:8]) for v in versions if v)}</span>'


def _usage_mean(
    trials: list[TrialSummary], reference: list[TrialSummary] | None, attribute: str, formatted,
) -> tuple[str, object]:
    """A usage mean's cell content and sort key, noting its relative change
    from the ``reference`` Trials' mean when both are known and nonzero."""
    value = mean_usage(trials, attribute)
    base = mean_usage(reference, attribute) if reference else None
    change = f' <span class="note">{100 * (value - base) / base:+.0f}%</span>' if value and base else ""
    return formatted(value) + change, value


# --- Trial page parts --------------------------------------------------------


def _checks_table(checks: list[dict], found: dict, labelled: dict) -> str:
    seen = {item["check"]: item for item in found["expected_value_seen"] or []}
    rows = "".join(
        f'<tr><td><span class="chip {"pass" if c["passed"] else "fail"}">{"passed" if c["passed"] else "failed"}</span></td>'
        f'<td class="mono">{escape(c["name"])}</td>'
        f'<td class="secondary">{"required" if c["required"] else "preferred"}</td>'
        f'<td class="wrapping"><pre>{escape(str(c.get("notes") or ""))}</pre>{_seen_note(seen.get(c["name"]))}'
        f'{_labels_note(labelled.get(c["name"]))}</td>'
        f'<td class="wrapping secondary">{_inline_markdown(c.get("description") or "")}</td></tr>'
        for c in sorted(checks, key=lambda c: (c["passed"], not c["required"]))
    )
    return ("<table><thead><tr><th>Result</th><th>Check</th><th>Tier</th><th>Notes</th><th>Description</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>")


def _seen_note(item: dict | None) -> str:
    if item is None:
        return ""
    return (f'<p class="note">expected <code>{escape(item["expected"])}</code>, '
            f'{"seen" if item["seen"] else "not seen"} in what the agent was shown</p>')


def _labels_note(answers: dict | None) -> str:
    """A failed check's saved Jev labels, each with its confidence."""
    if answers is None:
        return ""
    parts = [f'{question.replace("_", " ")} <code>{escape(str(answers[question]["choice"]))}</code> '
             f'({answers[question]["confidence"]})' for question in ("answer_source", "verification")]
    return f'<p class="note">{" · ".join(parts)} · {escape(str(answers["model"]))}</p>'


def _diagnostics(found: dict) -> str:
    """The Trial-level diagnostics, as facts under the checks table."""
    def listed(values: list[str] | None) -> str:
        if values is None:
            return '<span class="muted">unknown (no trajectory)</span>'
        return "<br>".join(f"<code>{escape(v)}</code>" for v in values) or '<span class="muted">none</span>'

    facts = []
    used = found["treatment_used"]
    if used is not None:
        facts.append(("Treatment skill", "loaded" if used["skill_loaded"] else "not loaded"))
        facts.append(("Treatment files named", listed(used["files_named"])))
    facts.append(("Deprecations shown to the agent", listed(found["deprecations_seen"])))
    facts.append(("Deprecations in application.log", listed(found["deprecations_logged"])))
    return '<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts) + "</dl>"


def _usage(trial: TrialSummary, usage: dict) -> str:
    counts = [
        ("Input tokens", usage.get("n_input_tokens")), ("Cache-read tokens", usage.get("n_cache_tokens")),
        ("Cache-write tokens", usage.get("n_cache_creation_tokens")), ("Output tokens", usage.get("n_output_tokens")),
    ]
    facts = [(label, f"{value:,}") for label, value in counts if value is not None]
    facts += [
        ("Cost (USD)", _format_cost(trial.cost_usd) or '<span class="muted">not reported</span>'),
        ("Turns", "" if trial.turns is None else str(trial.turns)),
        ("Agent execution", _format_duration(trial.duration_s)),
    ]
    tool_calls = usage.get("tool_calls") or {}
    if tool_calls:
        facts.append(("Tool calls", ", ".join(
            f"<code>{escape(name)}</code> {count}" for name, count in sorted(tool_calls.items(), key=lambda i: -i[1]))))
    html = '<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts if v) + "</dl>"
    for label, key in (("URLs", "urls"), ("Search queries", "search_queries")):
        values = usage.get(key) or []
        if values:
            items = "".join(f"<li><span class=\"mono\">{escape(str(v))}</span></li>" for v in values)
            html += f"<details><summary>{label} <span class=\"muted\">{len(values)}</span></summary><ul>{items}</ul></details>"
    return html


def _final_message(trajectory_file: Path) -> str:
    """The agent's last non-empty message, which usually reports what it did."""
    trajectory = _read_json(trajectory_file) or {}
    messages = [step["message"] for step in trajectory.get("steps") or []
                if step.get("source") == "agent" and isinstance(step.get("message"), str) and step["message"].strip()]
    if not messages:
        return ""
    return f'<h2>Final agent message</h2><pre class="message final">{escape(messages[-1])}</pre>'


def _transcript(steps: list[dict]) -> str:
    """Render trajectory steps: each message, its reasoning, and each tool
    call with its arguments and collapsed output."""
    started = _parse_time(steps[0].get("timestamp")) if steps else None
    items = []
    for step in steps:
        source = step.get("source", "")
        at = _parse_time(step.get("timestamp"))
        offset = _format_duration((at - started).total_seconds()) if at and started else ""
        outputs = {r.get("source_call_id"): r.get("content")
                   for r in (step.get("observation") or {}).get("results") or []}
        parts = [(f'<div class="step-head"><span class="chip source-{escape(source)}">{escape(source)}</span>'
                  f' <span class="muted">+{offset}</span></div>')]
        message = step.get("message") or ""
        if isinstance(message, str) and message:
            if source == "user":
                parts.append(f'<details><summary class="muted">Prompt</summary><pre>{escape(message)}</pre></details>')
            else:
                parts.append(f'<pre class="message">{escape(message)}</pre>')
        elif message:
            parts.append(f'<div class="tree">{_tree_children({"message": message}, open_depth=0)}</div>')
        if step.get("reasoning_content"):
            parts.append(f'<details><summary class="muted">Reasoning</summary>'
                         f'<pre>{escape(str(step["reasoning_content"]))}</pre></details>')
        for call in step.get("tool_calls") or []:
            arguments = call.get("arguments")
            arguments_html = (_tool_arguments(arguments) if isinstance(arguments, dict)
                              else f"<pre>{escape(json.dumps(arguments))}</pre>")
            output = outputs.get(call.get("tool_call_id"))
            if output is not None and not isinstance(output, str):
                output = json.dumps(output, indent=1)
            output_html = ""
            if output is not None:
                shown = output[:OUTPUT_LIMIT]
                cut = f"\n\u2026 {len(output) - len(shown):,} more characters in trajectory.json" if len(output) > len(shown) else ""
                output_html = (f'<details><summary class="muted">Output, {len(output):,} characters</summary>'
                               f'<pre class="output">{escape(shown + cut)}</pre></details>')
            parts.append(f'<div class="tool-call"><div class="tool-name">{escape(str(call.get("function_name", "")))}</div>'
                         f'<div class="tree">{arguments_html}</div>{output_html}</div>')
        items.append(f'<li class="step">{"".join(parts)}</li>')
    return f'<ol class="steps">{"".join(items)}</ol>'


def _tool_arguments(arguments: dict) -> str:
    # Strings print unquoted: a command or file body reads better as written.
    html = []
    for key, value in arguments.items():
        label = f'<span class="key">{escape(str(key))}</span>'
        if not isinstance(value, str):
            html.append(_tree_node(str(key), value, open_depth=0, depth=0))
        elif key == "command" or "\n" in value or len(value) > 160:
            html.append(f'<div class="leaf">{label}<pre class="string">{escape(value)}</pre></div>')
        else:
            html.append(f'<div class="leaf">{label}<span>{escape(value)}</span></div>')
    return "".join(html)


def _parse_time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def _tree_children(value: object, *, open_depth: int, depth: int = 0) -> str:
    """Render a JSON value's members as nested ``<details>``; members up to
    ``open_depth`` levels down start expanded."""
    if isinstance(value, dict):
        members = [(str(k), v) for k, v in value.items()]
        more = 0
    else:
        members = [(str(i), v) for i, v in enumerate(value[:LIST_LIMIT])]
        more = len(value) - len(members)
    html = "".join(_tree_node(k, v, open_depth=open_depth, depth=depth) for k, v in members)
    if more:
        html += f'<div class="leaf muted">&hellip; {more} more items; see the raw file</div>'
    return html


def _tree_node(key: str, value: object, *, open_depth: int, depth: int) -> str:
    label = f'<span class="key">{escape(key)}</span>'
    if isinstance(value, (dict, list)) and value:
        size = f"{{{len(value)}}}" if isinstance(value, dict) else f"[{len(value)}]"
        is_open = " open" if depth < open_depth else ""
        return (f'<details{is_open}><summary>{label}<span class="type">{size}</span></summary>'
                f'<div class="children">{_tree_children(value, open_depth=open_depth, depth=depth + 1)}</div></details>')
    if isinstance(value, str):
        if "\n" in value or len(value) > 160:
            return f'<div class="leaf">{label}<pre class="string">{escape(value)}</pre></div>'
        rendered = f'<span class="string">"{escape(value)}"</span>'
    elif isinstance(value, bool) or value is None:
        rendered = f'<span class="literal">{json.dumps(value)}</span>'
    elif isinstance(value, (int, float)):
        rendered = f'<span class="number">{value}</span>'
    else:
        rendered = f'<span class="type">{escape(json.dumps(value))}</span>'
    return f'<div class="leaf">{label}{rendered}</div>'


# --- Shared helpers ----------------------------------------------------------


class _Links:
    """Relative links from pages written in ``page_dir``."""

    def __init__(self, page_dir: Path):
        self.page_dir = page_dir

    def href(self, target: Path) -> str:
        return escape(os.path.relpath(target, self.page_dir))

    def link(self, target: Path, label: str, css: str = "") -> str:
        attributes = f' class="{css}"' if css else ""
        return f'<a href="{self.href(target)}"{attributes}>{escape(label)}</a>'

    def index(self, index: Path | None, **state: str) -> str:
        """A link to the index with tab and filter state; ``None`` is the index itself."""
        query = "&".join(f"{k}={quote(v, safe='/@')}" for k, v in state.items() if v)
        return (self.href(index) if index else "") + "#" + escape(query)


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{STYLE}</style>
</head>
<body>
{body}
</body>
</html>
"""


def _agents_with_runs(runs: list[RunSummary], agents: dict[str, dict]) -> list[str]:
    """Agent names with at least one run: ``agents.toml`` order, then any others by name."""
    with_runs = {run.agent for run in runs if run.agent}
    return [name for name in agents if name in with_runs] + sorted(with_runs - agents.keys())


def _agent_spec(agent: dict) -> str:
    return " ".join(str(agent[k]) for k in ("harness", "version", "model") if agent.get(k))


def _task_name(task: str) -> str:
    return task.removeprefix("tasks/")


def _check_ids(counts: Counter, css: str) -> str:
    return "".join(
        f'<span class="{css}">{escape(check)}{f" &times;{count}" if count > 1 else ""}</span>'
        for check, count in sorted(counts.items())
    )


def _inline_markdown(text: str) -> str:
    """Escape ``text`` and render its inline code spans; other Markdown stays as written."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escape(text))


def _fraction(passed: int, total: int, bar: str) -> tuple[str, object, str]:
    """A ``passed/total`` cell's content, sort key, and bar style; blank without a total."""
    if not total:
        return "", "", ""
    return f"{passed}/{total}", passed / total, f"--fraction: {100 * passed / total:.0f}%; --bar: var({bar})"


def _cell(content: str, sort_key: object, style: str = "", *, css: str = "") -> str:
    sort_key = "" if sort_key is None else sort_key
    attributes = f' class="{css}"' if css else ""
    attributes += f' style="{style}"' if style else ""
    return f'<td data-sort="{escape(str(sort_key))}"{attributes}>{content}</td>'


def _format_tokens(tokens: float | None) -> str:
    return "" if tokens is None else f"{tokens / 1000:,.0f}"


def _format_cost(cost: float | None) -> str:
    return "" if cost is None else f"{cost:.3f}"


def _format_duration(seconds: float | None) -> str:
    return "" if seconds is None else f"{int(seconds // 60)}m {int(seconds % 60):02d}s"


def _read_json(path: Path) -> object:
    return json.loads(path.read_text()) if path.is_file() else None
