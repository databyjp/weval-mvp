"""Render the report's HTML pages.

The index leads with the findings (every failed check as a ``FailureGroup``,
its saved judgments attached), then each Treatment comparison with a waffle
grid of its Trials, then each Task's reliability. Each Trial also gets its own
page with its checks, proposed classifications, usage, transcript, and
snapshot. All links are relative, so the pages work from ``file://``; view
state is carried by element anchors.
"""

import json
import os
import re
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

from weval.collect import (
    Comparison,
    RunSummary,
    TrialSummary,
    fisher_exact,
    mean_usage,
)
from weval.diagnostics import diagnose
from weval.labels import label
from weval.report.assets import LOGO, STYLE
from weval.report.findings import BASELINE, FailureGroup, TaskReliability

# A JSON array longer than this shows its first items and points to the raw file.
LIST_LIMIT = 50
# Transcript tool output beyond this many characters is left to trajectory.json.
OUTPUT_LIMIT = 6000
# The per-Trial files a page links to, when present.
KEY_FILES = (
    ("weval.json", "weval.json"),
    ("checks", "verifier/checks.json"),
    ("snapshot", "verifier/snapshot.json"),
    ("test output", "verifier/test-stdout.txt"),
    ("trajectory", "agent/trajectory.json"),
    ("submission", "artifacts/submission"),
)
ENVIRONMENTS = {"modal": "Modal", "docker": "local"}
# Waffle cells group by Trial status in this order, so an arm's pass rate
# reads as one block of colour; unknown statuses go last.
STATUS_ORDER = ("passed", "failed", "timed-out", "non-result", "incomplete")


def render_index(
    runs: list[RunSummary],
    analyses: list[tuple[Comparison, dict]],
    groups: list[FailureGroup],
    reliability: list[TaskReliability],
    *,
    index_dir: Path,
    trial_pages: dict[Path, Path],
    task_pages: dict[tuple[str, str], Path],
    generated: datetime,
) -> str:
    """Return ``index.html``. ``analyses`` pairs each Comparison with its
    saved ``analysis.analyse`` result; ``trial_pages`` maps each Trial
    directory to its page, and ``task_pages`` each ``(task, prompt variant)``
    to its Task page. Links are relative to ``index_dir``."""
    links = _Links(index_dir, task_pages)
    trial_count = sum(len(run.trials) for run in runs)
    tasks = sorted({run.task for run in runs})
    body = f"""
<header class="site"><h1>{LOGO}Weaviate Agent Experience (AX) Evaluation</h1>
<details class="how"><summary>How the evals work</summary><ul>
<li>Each <strong>Task</strong> gives a coding <strong>agent</strong> a real Weaviate job in a live environment.</li>
<li>A <strong>verifier</strong> then scores what the agent built against the Task's required and preferred <strong>checks</strong>.</li>
<li>A <strong>Treatment</strong> gives the agent extra skill files; its <strong>Trials</strong> are compared with <strong>baseline</strong> Trials run without them.</li>
<li><a href="#findings">Findings</a> lists every check that failed and why.</li>
<li><a href="#comparisons">Treatment comparisons</a> shows whether each Treatment helped.</li>
<li><a href="#reliability">Task reliability</a> says how much to trust each Task's numbers.</li>
</ul></details>
<span class="meta">{len(tasks)} Tasks, {len(runs)} runs, {trial_count} Trials, {len(groups)} findings.
Generated {generated:%Y-%m-%d %H:%M}.</span>
<nav class="sections"><a href="#findings">Findings</a><a href="#comparisons">Treatment comparisons</a>
<a href="#reliability">Task reliability</a></nav></header>
{_findings_section(groups, links, trial_pages)}
{_comparisons_section(analyses, links, trial_pages)}
{_reliability_section(reliability, links)}"""
    return _page("Weaviate AX Evaluation", body)


# --- Findings ----------------------------------------------------------------


def _findings_section(
    groups: list[FailureGroup], links: "_Links", trial_pages: dict[Path, Path]
) -> str:
    intro = (
        "Each card is one check that failed, with how often it failed in each arm: the bar fills to "
        "the failure rate. The counts come straight from the retained records. Everything else "
        "on a card is a saved opinion about why "
        "it failed, and each opinion names its judge: the LLM analyst, a hand-coded rule, or the Jev "
        "labeller. Open a failing Trial to see the evidence; the final call on a class is yours."
    )
    blocks = "".join(_finding(group, links, trial_pages) for group in groups)
    if not blocks:
        blocks = '<p class="muted">No failed checks are retained.</p>'
    return f'<h2 id="findings">Findings{_count(groups)}</h2>{_intro(intro)}{blocks}'


def _finding(
    group: FailureGroup, links: "_Links", trial_pages: dict[Path, Path]
) -> str:
    # The skeleton stays scannable: one line per arm, the fail counts as a
    # waffle (red = failed this check) rather than a sentence to parse.
    requires = []
    if group.description:
        requires.append(("Requires", _inline_markdown(group.description)))
    # One block of arm rows per Agent: a failure rate pooled across Agents
    # would describe none of them.
    by_agent: dict[str, list[tuple[str, str]]] = {}
    for (agent, arm), (failed, scored) in group.arms.items():
        label = escape(arm) if arm == BASELINE else f"+ {escape(arm)}"
        by_agent.setdefault(agent, []).append((label, _rate(failed, scored, "failed")))
    panel = "".join(
        f'<div class="agent">{escape(agent)}</div>{_facts(rows)}'
        for agent, rows in by_agent.items()
    )
    failing = (
        f"{len(group.failing)} failing Trial{'' if len(group.failing) == 1 else 's'}"
    )
    parts = [
        _card_head(
            escape(group.check),
            f'<span class="muted">proposed cause</span> {_class_chip(group.proposed_class)}',
            [
                links.task(group.task, group.prompt_variant),
                f"{'required' if group.required else 'preferred'} check",
                failing,
            ],
        ),
        _facts(requires),
        f'<div class="panel">{panel}</div>',
    ]

    # Everything below the skeleton folds away, so a page of cards stays
    # scannable. Inside, the analyst's pattern covers the whole check, and
    # the per-Trial judges (the rule and Jev) share one table.
    folded = ["<summary>Why it failed</summary>"]
    for pattern in group.patterns:
        folded.append(
            _judgment(
                f"proposes {_class_chip(pattern['class'])}",
                f"{pattern['model']}, reading the {pattern['treatment']} comparison",
                [
                    ("What happened", escape(pattern["summary"])),
                    ("Evidence", escape(pattern["evidence"])),
                    ("Reasoning", escape(pattern["reason"])),
                ],
            )
        )
    folded.append(_failing_trials(group, links, trial_pages))
    parts.append(f'<details class="more">{"".join(folded)}</details>')
    anchor = _finding_anchor(group.task, group.prompt_variant, group.check)
    return f'<div class="card" id="{anchor}">{"".join(parts)}</div>'


def _failing_trials(
    group: FailureGroup, links: "_Links", trial_pages: dict[Path, Path]
) -> str:
    """One row per Trial that failed the check, with the per-Trial judges'
    opinions; a rule class that contradicts the analyst is marked in place."""
    rule = {row["trial"]: row for row in group.proposals}
    disputed = {row["trial"] for row in group.disputed}
    rows = []
    # By Agent, baseline first, as in the card's arm panel.
    failing = sorted(
        group.failing, key=lambda pair: (pair[0].agent, bool(pair[0].treatment))
    )
    for run, trial in failing:
        name = trial.path.name
        source = ""
        if name in group.sources:
            choice, confidence = group.sources[name]
            source = (
                f"{escape(choice.removeprefix('https://'))} "
                f'<span class="muted">{confidence}</span>'
            )
        proposed = reason = ""
        if name in rule:
            proposed = _class_chip(rule[name]["class"])
            if name in disputed:
                proposed += ' <span class="disputed">differs from analyst</span>'
            reason = escape(rule[name]["reason"])
        rows.append(
            "<tr>"
            f"<td>{links.link(trial_pages[trial.path], name, css='mono')}</td>"
            f"<td>{escape(run.agent)}</td>"
            f"<td>{f'+ {escape(run.treatment)}' if run.treatment else BASELINE}</td>"
            f'<td class="wrapping">{source}</td>'
            f"<td>{proposed}</td>"
            f'<td class="wrapping">{reason}</td></tr>'
        )
    return (
        '<div class="part"><div class="who"><span class="pill">Failing Trials</span>'
        '<span class="note">judged one by one by the hand-coded rule and Jev</span></div>'
        '<table class="plain trials"><thead><tr>'
        "<th>Trial</th><th>Agent</th><th>Arm</th><th>Jev's answer source</th>"
        "<th>Rule's class</th><th>Rule's reason</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


# --- Treatment comparisons ---------------------------------------------------


def _comparisons_section(
    analyses: list[tuple[Comparison, dict]],
    links: "_Links",
    trial_pages: dict[Path, Path],
) -> str:
    intro = (
        "Did the Treatment help? Each card compares one Treatment's Trials with baseline Trials of "
        "the same Task, Agent, and versions, one column per arm. Each bar fills to the pass rate; "
        "the p-value (Fisher's exact test) says how "
        "easily the difference in passes could be chance. Usage rows "
        "are means per Trial, and the last column gives the Treatment's change from the baseline. "
        "The analyst's text is the saved <code>weval analyse</code> answer; the report never calls "
        "the analyst itself."
    )
    blocks = "".join(
        _comparison(comparison, found, links, trial_pages)
        for comparison, found in analyses
    )
    if not blocks:
        blocks = '<p class="muted">No Treatment runs are retained.</p>'
    return f'<h2 id="comparisons">Treatment comparisons{_count(analyses)}</h2>{_intro(intro)}{blocks}'


def _comparison(
    comparison: Comparison,
    found: dict,
    links: "_Links",
    trial_pages: dict[Path, Path],
) -> str:
    # One column per arm keeps the table narrow however many checks fail or
    # usage measures are shown; the last column compares the Treatment with
    # the baseline.
    arms = [comparison.baseline, comparison.treated]
    trials = [[t for run in runs for t in run.trials] for runs in arms]
    scored = [[t for run in runs for t in run.scored] for runs in arms]
    passed = [sum(t.status == "passed" for t in arm) for arm in scored]

    def row(label: str, cells: list[str], change: str = "", css: str = "") -> str:
        values = "".join(f'<td class="{css}">{cell}</td>' for cell in cells)
        return (
            f'<tr><th>{label}</th>{values}<td class="{css} change">{change}</td></tr>'
        )

    def group(label: str) -> str:
        return f'<tr class="group"><th colspan="4">{label}</th></tr>'

    pass_change = ""
    if all(scored):
        p = fisher_exact(passed[1], len(scored[1]), passed[0], len(scored[0]))
        # A difference in passes only reads as a count when the arms match.
        if len(scored[0]) == len(scored[1]):
            gained = passed[1] - passed[0]
            pass_change = _delta(f"{gained:+d}", gained) + " "
        pass_change += f'<span class="note">p = {p:.2g}</span>'
    rows = [
        row(
            "Pass rate",
            [
                f'{_rate_bar(count, len(arm), "passed")}<span class="pct">{100 * count / len(arm):.0f}%</span>'
                if arm
                else ""
                for count, arm in zip(passed, scored)
            ],
            css="num",
        ),
        row(
            "Passed",
            [
                f"{count}/{len(arm)}" if arm else ""
                for count, arm in zip(passed, scored)
            ],
            pass_change,
            "num",
        ),
    ]

    failed = [Counter(c for t in arm for c in t.failed_required) for arm in scored]
    if any(failed):
        rows.append(group("Failed required checks"))
        for check in sorted(set(failed[0]) | set(failed[1])):
            anchor = "#" + _finding_anchor(
                comparison.task, comparison.prompt_variant, check
            )
            rows.append(
                row(
                    f'<a class="mono" href="{anchor}">{escape(check)}</a>',
                    [str(counts[check]) for counts in failed],
                    _delta(
                        f"{failed[1][check] - failed[0][check]:+d}",
                        failed[0][check] - failed[1][check],
                    )
                    if len(scored[0]) == len(scored[1])
                    else "",
                    css="num",
                )
            )

    rows.append(group("Mean per Trial"))
    for measure, attribute, formatted in (
        ("Cost (USD)", "cost_usd", _format_cost),
        ("Uncached input (k)", "uncached_input", _format_tokens),
        ("Turns", "turns", lambda v: "" if v is None else f"{v:.0f}"),
        ("Duration", "duration_s", _format_duration),
    ):
        base, treated = (mean_usage(arm, attribute) for arm in trials)
        change = ""
        if base and treated:
            relative = (treated - base) / base
            # Less usage is better; a change under 5% is shown without colour.
            change = _delta(
                f"{100 * relative:+.0f}%", 0 if abs(relative) < 0.05 else -relative
            )
        rows.append(row(measure, [formatted(base), formatted(treated)], change, "num"))

    table = (
        '<div class="panel"><table class="plain arms"><thead><tr><th></th>'
        f'<th class="num">{escape(BASELINE)}</th>'
        f'<th class="num">+ {escape(comparison.treatment)}</th>'
        '<th class="num">Change</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )
    versions = ", ".join(
        f"{name} {escape(version[:8])}"
        for name, version in (
            ("Treatment", comparison.treatment_version),
            ("Task", comparison.task_version),
            ("checks", comparison.check_version),
        )
        if version
    )
    head = _card_head(
        escape(comparison.treatment),
        f'<span class="muted">passed</span> {passed[0]}/{len(scored[0])} '
        f"&rarr; {passed[1]}/{len(scored[1])}",
        [
            links.task(comparison.task, comparison.prompt_variant),
            escape(comparison.agent),
            f"versions {versions}" if versions else "unversioned",
        ],
    )
    anchor = f"comparison-{escape(comparison.treatment)}-{_slug(comparison.task)}"
    return f'<div class="card" id="{anchor}">{head}{table}{_analysis(found, comparison)}</div>'


def _analysis(found: dict, comparison: Comparison) -> str:
    """A comparison's saved analysis: its result unfolded, then its rule
    disagreements, caveats, and open questions folded. The patterns
    themselves render in the findings section."""
    answer = found["analysis"]
    if not answer:
        reason = "; ".join(found["problems"]) or found["note"] or "not analysed"
        return _judgment("has no saved answer", "", [("Reason", escape(reason))])
    folded, counts = [], []
    if found["disagreements"]:
        items = "".join(
            f'<li><a class="mono" href="#{_finding_anchor(comparison.task, comparison.prompt_variant, d["check"])}">'
            f"{escape(d['check'])}</a> in {escape(d['trial'])}: the analyst says "
            f"{escape(d['analyst'])}, the rule says {escape(d['class'])}</li>"
            for d in found["disagreements"]
        )
        folded.append(("Rule disagreements", f"<ul>{items}</ul>"))
        counts.append(f"{len(found['disagreements'])} rule disagreements")
    for title, key in (("Caveats", "caveats"), ("Open questions", "open_questions")):
        if answer.get(key):
            items = "".join(f"<li>{escape(i)}</li>" for i in answer[key])
            folded.append((title, f"<ul>{items}</ul>"))
            counts.append(f"{len(answer[key])} {title.lower()}")
    more = ""
    if folded:
        more = (
            f'<details class="more"><summary>Caveats and open questions '
            f'<span class="note">{", ".join(counts)}</span></summary>{_facts(folded)}</details>'
        )
    return _judgment(
        "concludes",
        str(found["model"]),
        [("Result", escape(answer["result"]))],
        more,
    )


# --- Task reliability ----------------------------------------------------------


def _reliability_section(reliability: list[TaskReliability], links: "_Links") -> str:
    intro = (
        "Before trusting a number above, check its Task here, arm by arm. An oracle fixture means the reference "
        "solution's snapshot is kept in the test suite, so the checks are calibrated against a known "
        "good answer. Scorer flags count saved opinions that blame the check or the Task itself "
        "rather than the agent. A mixed run has both passing and failing Trials in the same arm: "
        "either the Task separates good runs from bad, or it is flaky. An arm that every Trial "
        "passes, or none does, cannot show a Treatment's effect. Open a Task for its "
        "definition and every retained run and Trial."
    )
    rows = "".join(_reliability_row(row, links) for row in reliability)
    return f"""
<h2 id="reliability">Task reliability{_count(reliability)}</h2>{_intro(intro)}
<div class="wrap"><table class="reliability">
<thead><tr><th>Task</th><th>Treatment</th><th>Passed</th><th class="num">Non-results</th>
<th class="num">Mixed runs</th><th class="num">Scorer flags</th><th class="num">Runs</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""


def _reliability_row(row: TaskReliability, links: "_Links") -> str:
    """The Task's arm rows; the Task's name and calibration, which hold for
    every arm, span them."""
    calibrated = (
        '<span class="chip pass">oracle fixture</span>'
        if row.calibrated
        else '<span class="chip partial">no fixture</span>'
    )
    task = (
        f'<td class="task" rowspan="{len(row.arms)}">'
        f"<div>{links.task(row.task, row.prompt_variant)}</div>{calibrated}</td>"
    )
    anchor = f' id="task-{_slug(row.task)}"'
    rows = []
    for i, arm in enumerate(row.arms):
        rows.append(
            f"<tr{anchor if i == 0 else ''}>{task if i == 0 else ''}"
            f"<td>{escape(arm.arm) if arm.arm == BASELINE else f'+ {escape(arm.arm)}'}</td>"
            f"<td>{_rate(arm.passed, arm.scored, 'passed')}</td>"
            f'<td class="num">{arm.non_results or ""}</td>'
            f'<td class="num">{arm.mixed_runs or ""}</td>'
            f'<td class="num">{arm.scorer_flags or ""}</td>'
            f'<td class="num">{len(arm.runs)}</td></tr>'
        )
    return "".join(rows)


# --- Waffle grids --------------------------------------------------------------


def _rate_bar(count: int, total: int, outcome: str) -> str:
    """``count`` of ``total`` Trials as a bar on a 0-100% track, filled to
    the rate. ``outcome`` (``passed`` or ``failed``) names what is counted
    and sets the bar's colour; the tooltip states the figures in words."""
    if not total:
        return ""
    title = f"{count} of {total} {outcome} ({100 * count / total:.0f}%)"
    return (
        f'<span class="rate {outcome}" title="{title}">'
        f'<span class="fill" style="width: {100 * count / total:.1f}%"></span>'
        "</span>"
    )


def _rate(count: int, total: int, outcome: str) -> str:
    """A rate bar with its count written out beside it."""
    if not total:
        return f"0/0 {outcome}"
    return f"{_rate_bar(count, total, outcome)}{count}/{total} {outcome}"


def _cells(
    trials: list[TrialSummary], links: "_Links", trial_pages: dict[Path, Path]
) -> str:
    """One cell per Trial, coloured by status and grouped in ``STATUS_ORDER``;
    the sort is stable, so run order holds within a status."""

    def rank(trial: TrialSummary) -> int:
        if trial.status in STATUS_ORDER:
            return STATUS_ORDER.index(trial.status)
        return len(STATUS_ORDER)

    return "".join(
        f'<a class="status-{escape(trial.status)}" href="{links.href(trial_pages[trial.path])}" '
        f'title="{escape(trial.path.name)}: {escape(trial.status)}"></a>'
        for trial in sorted(trials, key=rank)
    )


# --- Task page -----------------------------------------------------------------

# Task package directories, in reading order, by what they hold for a reader.
PACKAGE_PARTS = (
    ("environment", "Workspace"),
    ("tests", "Scoring"),
    ("solution", "Oracle solution"),
)


def render_task(
    row: TaskReliability,
    *,
    page_dir: Path,
    index: Path,
    trial_pages: dict[Path, Path],
    file_pages: dict[Path, Path],
    docs: Path | None = None,
) -> str:
    """Return one Task and prompt variant's page: the definition its newest
    run packaged (prompt, checks, and files) and every retained run, each
    with its Trials. ``file_pages`` maps packaged files to their rendered
    pages; a file without one links to the raw file. ``docs`` is the Task's
    page under ``docs/tasks/``, when one exists. Links are relative to
    ``page_dir``."""
    links = _Links(page_dir)
    newest = row.runs[0]
    package = newest.path / "task"
    version = (newest.fingerprints or {}).get("task")
    trial_count = sum(len(run.trials) for run in row.runs)

    facts = [
        ("Passed", _rate(row.passed, row.scored, "passed")),
        ("Runs", f"{len(row.runs)} runs, {trial_count} Trials"),
        (
            "Definition",
            "as packaged for "
            + links.link(newest.path, newest.path.name, css="mono")
            + (
                f' <span class="note">Task version {escape(version[:8])}</span>'
                if version
                else ""
            ),
        ),
    ]
    if docs:
        facts.append(("Documentation", links.link(docs, docs.name)))

    sections = [
        (
            f'<div class="breadcrumb"><a href="{links.href(index)}">&larr; Report</a>'
            ' <span class="muted">/ Task</span></div>'
        ),
        f"<h1>{LOGO}{escape(_task_name(row.task))}{_variant_note(row.prompt_variant)}</h1>",
        _facts(facts),
    ]
    prompt_file = package / "instruction.md"
    if prompt_file.is_file():
        sections.append(
            "<h2>Prompt</h2>"
            '<p class="intro">Exactly what the agent was told, including the shared '
            "Trial-environment notes appended to every Task. Raw file: "
            f"{links.link(prompt_file, 'instruction.md')}.</p>"
            f'<div class="card"><pre class="message">{escape(prompt_file.read_text())}</pre></div>'
        )
    sections.append(
        "<h2>Checks</h2>"
        + _task_checks(row, index, links, package / "tests/check.py", file_pages)
    )
    sections.append(
        "<h2>Files</h2>"
        '<p class="intro">The Task package as the newest run built it.</p>'
        + _package_files(package, links, file_pages)
    )
    sections.append("<h2>Runs</h2>" + _task_runs(row, links, trial_pages))
    return _page(_task_name(row.task), "\n".join(sections))


def _task_checks(
    row: TaskReliability,
    index: Path,
    links: "_Links",
    check_file: Path,
    file_pages: dict[Path, Path],
) -> str:
    """The newest run's checks, each with its failure rate over the retained
    Trials that recorded it; a check that failed links to its finding, and
    each check links to its definition in ``check_file`` when that file has
    a rendered page."""
    newest = next(
        (t.record for t in row.runs[0].trials if t.record and t.record.get("checks")),
        None,
    )
    if not newest:
        return '<p class="muted">No checks recorded.</p>'
    scored = [t for run in row.runs for t in run.scored]
    check_page = file_pages.get(check_file)
    defined = _definition_lines(check_file) if check_page else {}
    rows = []
    for check in newest["checks"]:
        name = check["name"]
        recorded = [
            t
            for t in scored
            if any(c["name"] == name for c in (t.record or {}).get("checks") or [])
        ]
        failed = sum(
            name in t.failed_required or name in t.failed_preferred for t in recorded
        )
        title = escape(name)
        if failed:
            anchor = _finding_anchor(row.task, row.prompt_variant, name)
            title = f'<a href="{links.href(index)}#{anchor}">{title}</a>'
        if name in defined:
            title += (
                f' <a class="note" href="{links.href(check_page)}#L-{defined[name]}">'
                "source</a>"
            )
        rows.append(
            f'<tr><td class="mono">{title}</td>'
            f"<td>{'required' if check.get('required') else 'preferred'}</td>"
            f'<td class="wrapping">{_inline_markdown(check.get("description") or "")}</td>'
            f"<td>{_rate(failed, len(recorded), 'failed')}</td></tr>"
        )
    intro = (
        f'<p class="intro">Defined in {links.link(check_page, "check.py")}; each '
        "source link opens a check's function.</p>"
        if check_page
        else ""
    )
    return (
        intro
        + '<div class="card"><table class="plain trials"><thead><tr><th>Check</th><th>Kind</th>'
        "<th>Requires</th><th>Failed</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _definition_lines(check_file: Path) -> dict[str, int]:
    """Each top-level function in ``check_file`` by line number, keyed by
    check ID (the function name with dashes for underscores)."""
    lines = {}
    for number, line in enumerate(check_file.read_text().splitlines(), start=1):
        if match := re.match(r"def (\w+)\(", line):
            lines[match[1].replace("_", "-")] = number
    return lines


def _package_files(package: Path, links: "_Links", file_pages: dict[Path, Path]) -> str:
    """Links to every file in the Task package, grouped by what each part
    holds; files outside the named parts are listed as the package itself.
    Each links to its rendered page, else to the raw file."""
    if not package.is_dir():
        return '<p class="muted">The run kept no Task package.</p>'
    groups: dict[str, list[str]] = {label: [] for _, label in PACKAGE_PARTS}
    groups["Package"] = []
    names = dict(PACKAGE_PARTS)
    for path in sorted(p for p in package.rglob("*") if p.is_file()):
        relative = path.relative_to(package)
        label = (
            names.get(relative.parts[0], "Package")
            if len(relative.parts) > 1
            else "Package"
        )
        groups[label].append(
            links.link(file_pages.get(path, path), str(relative), css="mono")
        )
    return _facts(
        [(label, "<br>".join(files)) for label, files in groups.items() if files]
    )


def _task_runs(
    row: TaskReliability, links: "_Links", trial_pages: dict[Path, Path]
) -> str:
    rows = []
    for run in row.runs:
        passed = sum(t.status == "passed" for t in run.scored)
        version = (run.fingerprints or {}).get("task") or ""
        rows.append(
            f"<tr><td>{links.link(run.path, run.date.strftime('%Y-%m-%d %H:%M') if run.date else run.path.name)}</td>"
            f"<td>{escape(run.agent)}</td>"
            f"<td>{f'+ {escape(run.treatment)}' if run.treatment else BASELINE}</td>"
            f'<td class="mono">{escape(version[:8])}</td>'
            f'<td class="num">{passed}/{len(run.scored)}</td>'
            f'<td class="wrapping"><span class="waffle small">{_cells(run.trials, links, trial_pages)}</span></td></tr>'
        )
    return (
        '<p class="intro">Newest first. Each square is one Trial, passes first; click it to open '
        "that Trial.</p>"
        '<div class="card"><table class="plain trials"><thead><tr><th>Run</th><th>Agent</th>'
        '<th>Arm</th><th>Task version</th><th class="num">Passed</th><th>Trials</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


# --- Trial page ----------------------------------------------------------------


def render_trial(
    run: RunSummary,
    trial: TrialSummary,
    *,
    page_dir: Path,
    index: Path,
    task_page: Path,
    expected: dict | None = None,
    proposals: dict[str, list[dict]] | None = None,
) -> str:
    """Return one Trial's page; links are relative to ``page_dir``, and the
    Task's name links to ``task_page``.
    ``expected`` is the Task's ``EXPECTED``, for the checks' diagnostics;
    ``proposals`` maps a failed check to its saved class proposals, each
    ``{"class", "who", "reason"}``."""
    links = _Links(page_dir, {(run.task, run.prompt_variant): task_page})
    record = trial.record or {}
    agent = record.get("agent") or {}
    usage = record.get("usage") or {}

    facts = [
        (
            "Status",
            f'<span class="chip status-{escape(trial.status)}">{escape(trial.status)}</span>'
            + (
                f' <span class="note">reward {record["reward"]}</span>'
                if record.get("reward") is not None
                else ""
            ),
        ),
        ("Task", links.task(run.task, run.prompt_variant)),
        ("Prompt variant", escape(run.prompt_variant)),
        (
            "Agent",
            escape(run.agent)
            + (
                f' <span class="note">{escape(_agent_spec(agent))}</span>'
                if agent
                else ""
            ),
        ),
        ("Date", run.date.strftime("%Y-%m-%d %H:%M") if run.date else ""),
        ("Environment", escape(_environment(run))),
        ("Run", links.link(run.path, run.path.name, css="mono")),
        ("Trial", links.link(trial.path, trial.path.name, css="mono")),
    ]
    if record.get("exception"):
        facts.append(
            (
                "Exception",
                f'<span class="mono">{escape(str(record["exception"]))}</span>',
            )
        )
    if record.get("error_stage"):
        facts.append(("Error stage", escape(str(record["error_stage"]))))
    if record.get("missing_logs"):
        facts.append(
            (
                "Missing logs",
                ", ".join(
                    f"<code>{escape(str(m))}</code>" for m in record["missing_logs"]
                ),
            )
        )

    checks = (
        _read_json(trial.path / "verifier/checks.json") or record.get("checks") or []
    )
    snapshot_file = trial.path / "verifier/snapshot.json"
    snapshot = _read_json(snapshot_file)
    prompt_file = run.path / "task/instruction.md"
    found = diagnose(trial.path, expected or {}, snapshot or {}, checks)
    # Saved labels only: building the report never calls Jev.
    labelled = label(trial.path, checks, call=False)["labels"]

    sections = [
        (
            f'<div class="breadcrumb"><a href="{links.href(index)}">&larr; Report</a>'
            f' <span class="muted">/ {escape(run.path.name)}</span></div>'
        ),
        f'<h1>{LOGO}{escape(_task_name(run.task))} <span class="muted">with</span> {escape(run.agent)}</h1>',
        '<dl class="facts">'
        + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)
        + "</dl>",
        _final_message(trial.path / "agent/trajectory.json"),
        "<h2>Checks</h2>"
        + (
            _checks_table(checks, found, labelled, proposals or {})
            if checks
            else '<p class="muted">No checks recorded.</p>'
        )
        + _diagnostics(found),
        "<h2>Usage</h2>" + _usage(trial, usage),
        "<h2>Files</h2>"
        + '<p class="links">'
        + "".join(
            links.link(trial.path / rel, name)
            for name, rel in KEY_FILES
            if (trial.path / rel).exists()
        )
        + "</p>",
    ]
    trajectory = _read_json(trial.path / "agent/trajectory.json")
    if trajectory:
        sections.append(
            "<h2>Transcript</h2>"
            f'<p class="intro">Harbor\'s trajectory, step by step. Raw file: '
            f"{links.link(trial.path / 'agent/trajectory.json', 'trajectory.json')}.</p>"
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
            f'<h2>weval.json</h2><details><summary class="muted">All fields</summary>'
            f'<div class="tree">{_tree_children(trial.record, open_depth=0)}</div></details>'
        )
    return _page(f"{_task_name(run.task)} with {run.agent}", "\n".join(sections))


def _checks_table(
    checks: list[dict], found: dict, labelled: dict, proposals: dict[str, list[dict]]
) -> str:
    seen = {item["check"]: item for item in found["expected_value_seen"] or []}
    rows = "".join(
        f'<tr><td><span class="chip {"pass" if c["passed"] else "fail"}">{"passed" if c["passed"] else "failed"}</span></td>'
        f'<td class="mono">{escape(c["name"])}</td>'
        f'<td class="secondary">{"required" if c["required"] else "preferred"}</td>'
        f'<td class="wrapping"><pre>{escape(str(c.get("notes") or ""))}</pre>{_seen_note(seen.get(c["name"]))}'
        f"{_labels_note(labelled.get(c['name']))}{_proposals_note(None if c['passed'] else proposals.get(c['name']))}</td>"
        f'<td class="wrapping secondary">{_inline_markdown(c.get("description") or "")}</td></tr>'
        for c in sorted(checks, key=lambda c: (c["passed"], not c["required"]))
    )
    return (
        "<table><thead><tr><th>Result</th><th>Check</th><th>Tier</th><th>Notes</th><th>Description</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _proposals_note(rows: list[dict] | None) -> str:
    """A failed check's saved class proposals, each named with its judge."""
    if not rows:
        return ""
    parts = [
        f"{_class_chip(row['class'])} <span class='muted'>{escape(row['who'])}: {escape(row['reason'])}</span>"
        for row in rows
    ]
    return f'<p class="note">{"<br>".join(parts)}</p>'


def _seen_note(item: dict | None) -> str:
    if item is None:
        return ""
    return (
        f'<p class="note">expected <code>{escape(item["expected"])}</code>, '
        f"{'seen' if item['seen'] else 'not seen'} in what the agent was shown</p>"
    )


def _labels_note(answers: dict | None) -> str:
    """A failed check's saved Jev labels, each with its confidence."""
    if answers is None:
        return ""
    parts = [
        f"{question.replace('_', ' ')} <code>{escape(str(answers[question]['choice']))}</code> "
        f"({answers[question]['confidence']})"
        for question in ("answer_source", "verification")
    ]
    return f'<p class="note">{" · ".join(parts)} · {escape(str(answers["model"]))}</p>'


def _diagnostics(found: dict) -> str:
    """The Trial-level diagnostics, as facts under the checks table."""

    def listed(values: list[str] | None) -> str:
        if values is None:
            return '<span class="muted">unknown (no trajectory)</span>'
        return (
            "<br>".join(f"<code>{escape(v)}</code>" for v in values)
            or '<span class="muted">none</span>'
        )

    facts = []
    used = found["treatment_used"]
    if used is not None:
        facts.append(
            ("Treatment skill", "loaded" if used["skill_loaded"] else "not loaded")
        )
        facts.append(("Treatment files named", listed(used["files_named"])))
    facts.append(
        ("Deprecations shown to the agent", listed(found["deprecations_seen"]))
    )
    facts.append(
        ("Deprecations in application.log", listed(found["deprecations_logged"]))
    )
    return (
        '<dl class="facts">'
        + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)
        + "</dl>"
    )


def _usage(trial: TrialSummary, usage: dict) -> str:
    counts = [
        ("Input tokens", usage.get("n_input_tokens")),
        ("Cache-read tokens", usage.get("n_cache_tokens")),
        ("Cache-write tokens", usage.get("n_cache_creation_tokens")),
        ("Output tokens", usage.get("n_output_tokens")),
    ]
    facts = [(name, f"{value:,}") for name, value in counts if value is not None]
    facts += [
        (
            "Cost (USD)",
            _format_cost(trial.cost_usd) or '<span class="muted">not reported</span>',
        ),
        ("Turns", "" if trial.turns is None else str(trial.turns)),
        ("Agent execution", _format_duration(trial.duration_s)),
    ]
    tool_calls = usage.get("tool_calls") or {}
    if tool_calls:
        facts.append(
            (
                "Tool calls",
                ", ".join(
                    f"<code>{escape(name)}</code> {count}"
                    for name, count in sorted(tool_calls.items(), key=lambda i: -i[1])
                ),
            )
        )
    html = (
        '<dl class="facts">'
        + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts if v)
        + "</dl>"
    )
    for title, key in (("URLs", "urls"), ("Search queries", "search_queries")):
        values = usage.get(key) or []
        if values:
            items = "".join(
                f'<li><span class="mono">{escape(str(v))}</span></li>' for v in values
            )
            html += f'<details><summary>{title} <span class="muted">{len(values)}</span></summary><ul>{items}</ul></details>'
    return html


def _final_message(trajectory_file: Path) -> str:
    """The agent's last non-empty message, which usually reports what it did."""
    trajectory = _read_json(trajectory_file) or {}
    messages = [
        step["message"]
        for step in trajectory.get("steps") or []
        if step.get("source") == "agent"
        and isinstance(step.get("message"), str)
        and step["message"].strip()
    ]
    if not messages:
        return ""
    return f'<h2>Final agent message</h2><div class="final">{_block_markdown(messages[-1])}</div>'


def _transcript(steps: list[dict]) -> str:
    """Render trajectory steps: each message, its reasoning, and each tool
    call with its arguments and collapsed output."""
    started = _parse_time(steps[0].get("timestamp")) if steps else None
    items = []
    for step in steps:
        source = step.get("source", "")
        at = _parse_time(step.get("timestamp"))
        offset = (
            _format_duration((at - started).total_seconds()) if at and started else ""
        )
        outputs = {
            r.get("source_call_id"): r.get("content")
            for r in (step.get("observation") or {}).get("results") or []
        }
        parts = []
        message = step.get("message") or ""
        if isinstance(message, str) and message:
            if source == "user":
                parts.append(
                    f'<details><summary class="muted">Prompt</summary><pre>{escape(message)}</pre></details>'
                )
            else:
                parts.append(f'<pre class="message">{escape(message)}</pre>')
        elif message:
            parts.append(
                f'<div class="tree">{_tree_children({"message": message}, open_depth=0)}</div>'
            )
        if step.get("reasoning_content"):
            parts.append(
                f'<details><summary class="muted">Reasoning</summary>'
                f"<pre>{escape(str(step['reasoning_content']))}</pre></details>"
            )
        for call in step.get("tool_calls") or []:
            arguments = call.get("arguments")
            arguments_html = (
                _tool_arguments(arguments)
                if isinstance(arguments, dict)
                else f"<pre>{escape(json.dumps(arguments))}</pre>"
            )
            output = outputs.get(call.get("tool_call_id"))
            if output is not None and not isinstance(output, str):
                output = json.dumps(output, indent=1)
            output_html = ""
            if output is not None:
                shown = output[:OUTPUT_LIMIT]
                cut = (
                    f"\n… {len(output) - len(shown):,} more characters in trajectory.json"
                    if len(output) > len(shown)
                    else ""
                )
                output_html = (
                    f'<details><summary class="muted">Output, {len(output):,} characters</summary>'
                    f'<pre class="output">{escape(shown + cut)}</pre></details>'
                )
            parts.append(
                f'<div class="tool-call"><div class="tool-name">{escape(str(call.get("function_name", "")))}</div>'
                f'<div class="tree">{arguments_html}</div>{output_html}</div>'
            )
        # Each step folds to its headline, so a long Trial stays one screen;
        # the preview names what the fold holds.
        head = (
            f'<summary class="step-head"><span class="chip source-{escape(source)}">{escape(source)}</span>'
            f' <span class="muted">+{offset}</span>'
            f' <span class="preview">{_step_preview(step)}</span></summary>'
        )
        items.append(f'<li class="step"><details>{head}{"".join(parts)}</details></li>')
    return f'<ol class="steps">{"".join(items)}</ol>'


def _step_preview(step: dict) -> str:
    """A step's one-line summary: the first line of its message, and the
    names of the tools it called."""
    parts = []
    message = step.get("message")
    if isinstance(message, str) and message.strip():
        first = message.strip().splitlines()[0]
        shown = first[:110]
        parts.append(escape(shown + ("" if shown == message.strip() else "…")))
    tools = Counter(
        str(call.get("function_name", "")) for call in step.get("tool_calls") or []
    )
    if tools:
        names = ", ".join(
            f"{escape(name)}{f' &times;{count}' if count > 1 else ''}"
            for name, count in sorted(tools.items())
        )
        parts.append(f'<span class="mono">{names}</span>')
    return " &middot; ".join(parts)


def _tool_arguments(arguments: dict) -> str:
    # Strings print unquoted: a command or file body reads better as written.
    html = []
    for key, value in arguments.items():
        label = f'<span class="key">{escape(str(key))}</span>'
        if not isinstance(value, str):
            html.append(_tree_node(str(key), value, open_depth=0, depth=0))
        elif key == "command" or "\n" in value or len(value) > 160:
            html.append(
                f'<div class="leaf">{label}<pre class="string">{escape(value)}</pre></div>'
            )
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
    html = "".join(
        _tree_node(k, v, open_depth=open_depth, depth=depth) for k, v in members
    )
    if more:
        html += f'<div class="leaf muted">&hellip; {more} more items; see the raw file</div>'
    return html


def _tree_node(key: str, value: object, *, open_depth: int, depth: int) -> str:
    label = f'<span class="key">{escape(key)}</span>'
    if isinstance(value, (dict, list)) and value:
        size = f"{{{len(value)}}}" if isinstance(value, dict) else f"[{len(value)}]"
        is_open = " open" if depth < open_depth else ""
        return (
            f'<details{is_open}><summary>{label}<span class="type">{size}</span></summary>'
            f'<div class="children">{_tree_children(value, open_depth=open_depth, depth=depth + 1)}</div></details>'
        )
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
    """Relative links from pages written in ``page_dir``. ``task_pages`` maps
    each ``(task, prompt variant)`` to its Task page."""

    def __init__(
        self, page_dir: Path, task_pages: dict[tuple[str, str], Path] | None = None
    ):
        self.page_dir = page_dir
        self.task_pages = task_pages or {}

    def task(self, task: str, prompt_variant: str) -> str:
        """The Task's name, linked to its page when one was written."""
        name = f"{escape(_task_name(task))}{_variant_note(prompt_variant)}"
        page = self.task_pages.get((task, prompt_variant))
        return f'<a href="{self.href(page)}">{name}</a>' if page else name

    def href(self, target: Path) -> str:
        return escape(os.path.relpath(target, self.page_dir))

    def link(self, target: Path, label: str, css: str = "") -> str:
        attributes = f' class="{css}"' if css else ""
        return f'<a href="{self.href(target)}"{attributes}>{escape(label)}</a>'


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


def _environment(run: RunSummary) -> str:
    """Where the run executed, from Harbor's job config."""
    config = _read_json(run.path / "job/config.json") or {}
    kind = (config.get("environment") or {}).get("type", "")
    return ENVIRONMENTS.get(kind, kind)


def _class_chip(name: str) -> str:
    css = "class-" + name.replace(" ", "-").lower()
    return f'<span class="chip {css}">{escape(name)}</span>'


def _variant_note(prompt_variant: str) -> str:
    return "" if prompt_variant == "default" else f"@{escape(prompt_variant)}"


def _card_head(title: str, aside: str, sub: list[str]) -> str:
    """The head shared by finding and comparison cards: the subject's
    identifier, its one-glance outcome at the right, and a context line."""
    return (
        f'<div class="card-head"><div class="head"><span class="title mono">{title}</span>'
        f'<span class="aside">{aside}</span></div>'
        f'<div class="sub">{" &middot; ".join(sub)}</div></div>'
    )


def _delta(text: str, direction: float) -> str:
    """A Treatment-versus-baseline change, coloured by ``direction``:
    positive is better for the Treatment, negative worse, zero neutral."""
    css = "better" if direction > 0 else "worse" if direction < 0 else ""
    return f'<span class="delta {css}">{text}</span>'


def _judgment(
    verdict: str, provenance: str, rows: list[tuple[str, str]], more: str = ""
) -> str:
    """One saved opinion of the LLM analyst: what it says, which model said it
    and where, its labelled fields, and ``more`` folded material of its own."""
    source = f' <span class="note">{escape(provenance)}</span>' if provenance else ""
    return (
        f'<div class="part judgment"><div class="who"><span class="pill">LLM analyst</span> {verdict}{source}</div>'
        f"{_facts(rows)}{more}</div>"
    )


def _facts(rows: list[tuple[str, str]]) -> str:
    return (
        '<dl class="facts">'
        + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
        + "</dl>"
    )


def _count(items: list) -> str:
    return f' <span class="count">{len(items)}</span>' if items else ""


def _intro(text: str) -> str:
    """A section's reading instructions, folded so they do not compete with
    the content; the full text stays one click away for first-time readers."""
    return (
        '<details class="how"><summary>How to read this section</summary>'
        f'<p class="intro">{text}</p></details>'
    )


def _agent_spec(agent: dict) -> str:
    return " ".join(
        str(agent[k]) for k in ("harness", "version", "model") if agent.get(k)
    )


def _task_name(task: str) -> str:
    return task.removeprefix("tasks/")


def _finding_anchor(task: str, prompt_variant: str, check: str) -> str:
    return escape(f"finding-{_slug(task)}-{prompt_variant}-{check}")


def _slug(task: str) -> str:
    return _task_name(task).replace("/", "-")


def _inline_markdown(text: str) -> str:
    """Escape ``text`` and render its inline code spans and bold runs; other
    Markdown stays as written."""
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", escape(text))
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)


def _block_markdown(text: str) -> str:
    """Render the Markdown blocks agents write in their messages: headings,
    bullet and numbered lists (a wrapped item's following lines stay in that
    item), fenced code, and paragraphs, with ``_inline_markdown`` inside each.
    Unrecognised syntax stays as written."""
    html: list[str] = []
    paragraph: list[str] = []
    items: list[str] = []
    list_tag = ""
    fence: list[str] | None = None

    def flush() -> None:
        nonlocal list_tag
        if paragraph:
            html.append(f"<p>{_inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()
        if items:
            rendered = "".join(f"<li>{_inline_markdown(i)}</li>" for i in items)
            html.append(f"<{list_tag}>{rendered}</{list_tag}>")
            items.clear()
            list_tag = ""

    for line in text.splitlines():
        if fence is not None:
            if line.lstrip().startswith("```"):
                html.append(f"<pre>{escape(chr(10).join(fence))}</pre>")
                fence = None
            else:
                fence.append(line)
            continue
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            fence = []
        elif not stripped:
            flush()
        elif heading := re.match(r"(#{1,6}) +(.*)", stripped):
            flush()
            tag = "h3" if len(heading[1]) <= 2 else "h4"
            html.append(f"<{tag}>{_inline_markdown(heading[2])}</{tag}>")
        elif item := re.match(r"[-*] +(.*)", stripped):
            if list_tag != "ul":
                flush()
                list_tag = "ul"
            items.append(item[1])
        elif item := re.match(r"\d+[.)] +(.*)", stripped):
            if list_tag != "ol":
                flush()
                list_tag = "ol"
            items.append(item[1])
        elif items:  # A continuation line, as CommonMark reads it.
            items[-1] += f" {stripped}"
        else:
            paragraph.append(stripped)
    if fence is not None:  # An unclosed fence still shows its lines.
        html.append(f"<pre>{escape(chr(10).join(fence))}</pre>")
    flush()
    return "".join(html)


def _format_tokens(tokens: float | None) -> str:
    return "" if tokens is None else f"{tokens / 1000:,.0f}"


def _format_cost(cost: float | None) -> str:
    return "" if cost is None else f"{cost:.3f}"


def _format_duration(seconds: float | None) -> str:
    return "" if seconds is None else f"{int(seconds // 60)}m {int(seconds % 60):02d}s"


def _read_json(path: Path) -> object:
    return json.loads(path.read_text()) if path.is_file() else None
