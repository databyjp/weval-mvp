"""The report's view-model and page writing: failure groups carry per-arm
counts computed from records alone, saved judgments attach as annotations with
provenance, Task reliability counts what erodes trust, and ``write_report``
renders a retained run offline, removing stale Trial pages.
"""

import json
import re
from pathlib import Path

from weval.collect import Comparison, RunSummary, TrialSummary
from weval.report import write_report
from weval.report.findings import TaskReliability, failure_groups, task_reliability
from weval.report.pages import (
    _block_markdown,
    _cells,
    _comparison,
    _findings_section,
    _labels_note,
    _Links,
    _task_runs,
    _transcript,
)

TASK = "tasks/build/x"


def make_trial(
    base: Path, name: str, status: str, failed: list[str] = ()
) -> TrialSummary:
    checks = [
        {
            "name": check,
            "required": True,
            "passed": check not in failed,
            "notes": f"{check} failed" if check in failed else "ok",
            "description": f"{check} description",
        }
        for check in ("vector-config", "other-check")
    ]
    return TrialSummary(
        path=base / "job" / name,
        status=status,
        record={"status": status, "checks": checks},
        failed_required=list(failed),
    )


def make_run(
    tmp_path: Path, name: str, treatment: str, trials, agent: str = "agent"
) -> RunSummary:
    base = tmp_path / name
    return RunSummary(
        path=base,
        date=None,
        task=TASK,
        prompt_variant="default",
        treatment=treatment,
        agent=agent,
        trials=[make_trial(base, *t) for t in trials],
    )


def test_failure_groups_count_every_arm_even_at_zero_failures(tmp_path):
    baseline = make_run(
        tmp_path,
        "20260101-000001__build__x__agent",
        "",
        [("t1", "failed", ["vector-config"]), ("t2", "failed", ["vector-config"])],
    )
    treated = make_run(
        tmp_path,
        "20260101-000002__build__x__agent+skills",
        "skills",
        [("t3", "passed"), ("t4", "failed", ["other-check"]), ("t5", "non-result")],
    )
    groups = {g.check: g for g in failure_groups([baseline, treated], [])}

    assert groups["vector-config"].arms == {"baseline": (2, 2), "skills": (0, 2)}
    assert groups["other-check"].arms == {"baseline": (0, 2), "skills": (1, 2)}
    # The non-result Trial is not scored, so it is in no count and no arm.
    skills = groups["vector-config"].arm_trials["skills"]
    assert [t.path.name for _, t in skills] == [
        "t3",
        "t4",
    ]
    assert groups["vector-config"].description == "vector-config description"
    assert [t.path.name for _, t in groups["other-check"].failing] == ["t4"]


def analysed(comparison: Comparison, patterns: list[dict], rule: list[dict]) -> tuple:
    return (
        comparison,
        {
            "analysis": {
                "result": "r",
                "patterns": patterns,
                "caveats": [],
                "open_questions": [],
            },
            "model": "analyst-model",
            "problems": [],
            "rule": rule,
            "disagreements": [],
            "note": None,
        },
    )


def test_failure_groups_count_each_arm_across_agents_and_name_the_failing_ones(
    tmp_path,
):
    claude = make_run(
        tmp_path,
        "20260101-000001__build__x__claude",
        "",
        [("t1", "failed", ["vector-config"]), ("t2", "passed")],
        agent="claude",
    )
    pi = make_run(
        tmp_path,
        "20260101-000002__build__x__pi",
        "",
        [("t3", "passed"), ("t4", "passed"), ("t5", "passed")],
        agent="pi",
    )
    (group,) = failure_groups([pi, claude], [])

    assert group.arms == {"baseline": (1, 5)}
    assert group.failing_agents == {"baseline": ["claude"]}


def test_saved_judgments_attach_to_the_groups(tmp_path):
    baseline = make_run(
        tmp_path,
        "20260101-000001__build__x__agent",
        "",
        [("t1", "failed", ["vector-config"]), ("t2", "failed", ["other-check"])],
    )
    treated = make_run(
        tmp_path,
        "20260101-000002__build__x__agent+skills",
        "skills",
        [("t3", "passed")],
    )
    comparison = Comparison(
        TASK,
        "default",
        "skills",
        baseline=[baseline],
        treated=[treated],
        agents=["agent"],
    )
    pattern = {
        "summary": "agents use the legacy vectorizer",
        "checks": ["vector-config"],
        "trials": ["t1"],
        "evidence": "e",
        "class": "Weaviate gap",
        "reason": "the docs page shows the legacy call",
    }
    rule = [
        {
            "trial": "t1",
            "check": "vector-config",
            "class": "Weaviate gap",
            "reason": "x",
        },
        {"trial": "t2", "check": "other-check", "class": "agent gap", "reason": "y"},
    ]
    groups = {
        g.check: g
        for g in failure_groups(
            [baseline, treated], [analysed(comparison, [pattern], rule)]
        )
    }

    assert groups["vector-config"].proposed_class == "Weaviate gap"
    assert groups["vector-config"].patterns[0]["model"] == "analyst-model"
    # No analyst pattern covers other-check: the rule's agreed class stands in.
    assert groups["other-check"].proposed_class == "agent gap"
    assert groups["other-check"].proposals == [rule[1]]


def test_findings_order_by_tier_then_baseline_rate_then_count(tmp_path):
    def run(name: str, treatment: str, failures: list[list[str]]) -> RunSummary:
        trials = [
            (f"{name}-{i}", "failed", failed) for i, failed in enumerate(failures)
        ]
        return make_run(tmp_path, name, treatment, trials)

    # Baseline rates: half-of-four 2/4, half-of-two 1/2, rare 1/4; style is a
    # preferred check failing 4/4. treated-only fails 1/1, but only with the
    # Treatment.
    baseline = run(
        "b",
        "",
        [["half-of-four", "rare"], ["half-of-four"], [], []],
    )
    other_task = make_run(
        tmp_path,
        "b2",
        "",
        [("b2-0", "failed", ["half-of-two"]), ("b2-1", "passed")],
    )
    other_task.task = "tasks/build/y"
    treated = run("t", "skills", [["treated-only"]])
    for trial in baseline.trials:
        trial.failed_preferred = ["style"]

    groups = failure_groups([baseline, other_task, treated], [])

    assert [g.check for g in groups] == [
        "half-of-four",  # 50%, 2 failing: the count breaks the tie
        "half-of-two",  # 50%, 1 failing
        "rare",  # 25%
        "treated-only",  # 100%, but only with the Treatment
        "style",  # preferred, after every required check
    ]
    assert groups[3].headline() == ("skills", 1, 1)


def test_findings_group_by_task_with_the_most_failures_first(tmp_path):
    # tasks/build/x fails 1 check in 1 Trial; tasks/build/y fails 2 checks
    # in 1 Trial and a preferred check in another, so it leads.
    x = make_run(tmp_path, "x", "", [("x-0", "failed", ["vector-config"])])
    y = make_run(
        tmp_path,
        "y",
        "",
        [("y-0", "failed", ["vector-config", "other-check"]), ("y-1", "passed")],
    )
    y.task = "tasks/build/y"
    y.trials[1].failed_preferred = ["style"]
    groups = failure_groups([x, y], [])
    pages = {t.path: tmp_path / f"{t.path.name}.html" for r in (x, y) for t in r.trials}

    html = _findings_section(groups, {}, _Links(tmp_path), pages)

    headings = re.findall(r"<h3>([^< ]+)", html)
    assert headings == ["build/y", "build/x"]
    style = re.search(r'<details class="fold preferred" id="[^"]*style"', html)
    assert style, "a preferred check's row carries the preferred class"
    assert '<span class="tier">preferred</span>' in html
    assert html.count('class="fold required"') == 3


def test_disagreeing_judges_leave_a_group_unclassified(tmp_path):
    run = make_run(
        tmp_path,
        "20260101-000001__build__x__agent",
        "",
        [("t1", "failed", ["vector-config"])],
    )
    comparison = Comparison(
        TASK, "default", "skills", baseline=[run], treated=[], agents=["agent"]
    )
    rule = [
        {"trial": "t1", "check": "vector-config", "class": "agent gap", "reason": "x"},
        {
            "trial": "t2",
            "check": "vector-config",
            "class": "Weaviate gap",
            "reason": "y",
        },
    ]
    (group,) = failure_groups([run], [analysed(comparison, [], rule)])
    assert group.proposed_class == "unclassified"


def test_a_comparison_card_shows_each_agent_and_what_the_treatment_did_to_it(
    tmp_path,
):
    def run(name: str, treatment: str, agent: str, status: str) -> RunSummary:
        failed = ["vector-config"] if status == "failed" else []
        return make_run(tmp_path, name, treatment, [(name, status, failed)], agent)

    runs = {
        ("claude", ""): run("b-claude", "", "claude", "failed"),
        ("claude", "skills"): run("t-claude", "skills", "claude", "passed"),
        ("pi", ""): run("b-pi", "", "pi", "passed"),
        ("pi", "skills"): run("t-pi", "skills", "pi", "failed"),
    }
    comparison = Comparison(
        TASK,
        "default",
        "skills",
        baseline=[runs["claude", ""], runs["pi", ""]],
        treated=[runs["claude", "skills"], runs["pi", "skills"]],
        agents=["claude", "pi"],
        unpaired=["gpt"],
    )
    pages = {
        t.path: tmp_path / f"{t.path.name}.html"
        for r in runs.values()
        for t in r.trials
    }
    found = {"analysis": None, "problems": [], "note": "not analysed"}

    html = _comparison(comparison, found, _Links(tmp_path), pages)

    assert "2 agents: 1 helped, 1 hurt" in html
    by_agent = html.split('class="plain arms by-agent"')[1].split("<tbody>")[1]
    rows = re.findall(r"<tr><th>(\w+)</th>", by_agent)
    assert rows == ["claude", "pi"]
    assert '<span class="delta better">helped</span>' in html
    assert '<span class="delta worse">hurt</span>' in html
    assert "Left out, with runs in one arm only: gpt" in html


def test_a_usage_row_shows_the_mean_and_median_change_and_which_way_agents_went(
    tmp_path,
):
    # One heavy Agent halves its cost while two light ones double theirs: the
    # mean falls, but most Agents went up.
    costs = {"heavy": (10.0, 5.0), "light-1": (1.0, 2.0), "light-2": (1.0, 2.0)}
    arms = {"": [], "skills": []}
    for agent, (baseline, treated) in costs.items():
        for treatment, cost in (("", baseline), ("skills", treated)):
            run = make_run(
                tmp_path, f"{agent}{treatment}", treatment, [(agent, "passed")], agent
            )
            run.trials[0].cost_usd = cost
            arms[treatment].append(run)
    comparison = Comparison(
        TASK,
        "default",
        "skills",
        baseline=arms[""],
        treated=arms["skills"],
        agents=list(costs),
    )
    pages = {
        t.path: tmp_path / f"{t.path.name}.html"
        for runs in arms.values()
        for r in runs
        for t in r.trials
    }
    found = {"analysis": None, "problems": [], "note": "not analysed"}

    html = _comparison(comparison, found, _Links(tmp_path), pages)

    cost = html.split("<th>Cost (USD)</th>")[1].split("</tr>")[0]
    assert "mean -25%" in cost
    assert "median +100%" in cost
    assert '<span class="delta worse">2 of 3 up</span>' in cost


def test_task_reliability_counts_what_erodes_trust_per_arm(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "build-x-oracle-snapshot.json").write_text("{}")
    mixed = make_run(
        tmp_path,
        "20260101-000001__build__x__agent",
        "",
        [("t1", "passed"), ("t2", "failed", ["vector-config"]), ("t3", "non-result")],
    )
    treated = make_run(
        tmp_path,
        "20260101-000002__build__x__agent+skills",
        "skills",
        [("t4", "passed"), ("t5", "passed")],
    )
    comparison = Comparison(
        TASK, "default", "skills", baseline=[mixed], treated=[treated], agents=["agent"]
    )
    rule = [
        {"trial": "t2", "check": "vector-config", "class": "scorer bug", "reason": "x"}
    ]
    # A pattern citing Trials of both arms flags each arm once.
    pattern = {
        "class": "Task defect",
        "checks": ["vector-config"],
        "trials": ["t2", "t4"],
    }
    found = analysed(comparison, [pattern], rule)
    (row,) = task_reliability([treated, mixed], [found], fixtures)

    assert row.calibrated
    assert (row.passed, row.scored) == (3, 4)
    baseline, skills = row.arms
    assert (baseline.arm, baseline.passed, baseline.scored) == ("baseline", 1, 2)
    assert (baseline.non_results, baseline.mixed_runs, baseline.scorer_flags) == (
        1,
        1,
        2,
    )
    assert (skills.arm, skills.passed, skills.scored) == ("skills", 2, 2)
    assert (skills.non_results, skills.mixed_runs, skills.scorer_flags) == (0, 0, 1)


def test_block_markdown_renders_the_blocks_agents_write():
    text = (
        "**Built** the `/search` endpoint.\n\n"
        "## What changed\n"
        "- added `page_size`\n"
        "- capped at 100\n\n"
        "```\ncurl 'http://x?q=<sku>'\n```\n"
        "Not a full test suite."
    )
    html = _block_markdown(text)
    assert "<p><strong>Built</strong> the <code>/search</code> endpoint.</p>" in html
    assert "<h3>What changed</h3>" in html
    assert "<li>added <code>page_size</code></li><li>capped at 100</li>" in html
    assert "<pre>curl &#x27;http://x?q=&lt;sku&gt;&#x27;</pre>" in html
    assert "<p>Not a full test suite.</p>" in html


def test_block_markdown_keeps_a_wrapped_list_item_in_its_item():
    text = (
        "Environment notes:\n"
        "- Your shell runs inside the container, so\n"
        "  `docker ps` lists it.\n"
        "- Restart it by stopping that process."
    )
    html = _block_markdown(text)
    assert html == (
        "<p>Environment notes:</p><ul>"
        "<li>Your shell runs inside the container, so <code>docker ps</code> lists it.</li>"
        "<li>Restart it by stopping that process.</li></ul>"
    )


def test_waffle_cells_group_by_outcome_in_run_order(tmp_path):
    trials = [
        make_trial(tmp_path, "t1", "failed", ["vector-config"]),
        make_trial(tmp_path, "t2", "passed"),
        make_trial(tmp_path, "t3", "non-result"),
        make_trial(tmp_path, "t4", "failed", ["vector-config"]),
        make_trial(tmp_path, "t5", "passed"),
    ]
    pages = {t.path: tmp_path / f"{t.path.name}.html" for t in trials}
    links = _Links(tmp_path)

    def order(html: str) -> list[str]:
        return re.findall(r'title="(t\d)', html)

    assert order(_cells(trials, links, pages)) == ["t2", "t5", "t1", "t4", "t3"]


def test_task_runs_show_each_trials_checks_with_required_first(tmp_path):
    run = make_run(
        tmp_path,
        "20260101-000001__build__x__agent",
        "",
        [("t1", "failed", ["vector-config"]), ("t2", "non-result")],
    )
    run.trials[0].record["checks"].insert(
        0, {"name": "server-version", "required": False, "passed": False}
    )
    run.trials[1].record = {"status": "non-result"}
    row = TaskReliability(TASK, "default", [run], 1, 0, False, [])
    pages = {t.path: tmp_path / f"{t.path.name}.html" for t in run.trials}

    html = _task_runs(row, _Links(tmp_path), pages)

    assert re.findall(r'<th class="check (\w+)"><span>([\w-]+)', html) == [
        ("required", "vector-config"),
        ("required", "other-check"),
        ("preferred", "server-version"),
    ]
    assert re.findall(r'title="(t\d): ([\w-]+) ([^"]+)"', html) == [
        ("t1", "vector-config", "failed"),
        ("t1", "other-check", "passed"),
        ("t1", "server-version", "failed"),
        ("t2", "vector-config", "not scored (non-result)"),
        ("t2", "other-check", "not scored (non-result)"),
        ("t2", "server-version", "not scored (non-result)"),
    ]
    assert html.split("<tbody>")[1].count('rowspan="2"') == 5


def test_write_report_renders_a_retained_run_and_removes_stale_pages(tmp_path):
    run_dir = tmp_path / "20260101-000001__build__x__agent"
    trial_dir = run_dir / "job" / "t1"
    trial_dir.mkdir(parents=True)
    (trial_dir / "weval.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "task": TASK,
                "prompt_variant": "default",
                "treatment": None,
                "fingerprints": None,
                "agent": {"name": "agent", "harness": "pi"},
                "reward": 0,
                "checks": [
                    {
                        "name": "vector-config",
                        "required": True,
                        "passed": False,
                        "notes": "collection uses the legacy vectorizer",
                        "description": "the collection configures a named vector",
                    }
                ],
                "usage": {"n_input_tokens": 10, "n_output_tokens": 5, "cost_usd": 0.01},
            }
        )
    )
    (run_dir / "task" / "environment").mkdir(parents=True)
    (run_dir / "task" / "instruction.md").write_text("Build **semantic search**.")
    (run_dir / "task" / "environment" / "WORKSPACE.md").write_text("notes")
    (run_dir / "task" / "tests").mkdir()
    (run_dir / "task" / "tests" / "check.py").write_text(
        "import json\n\n\ndef vector_config(snapshot):\n    pass\n"
    )
    (run_dir / "task" / "environment" / "data.bin").write_bytes(b"\xff\xfe\x00")
    stale = tmp_path / "_report" / "gone-run" / "gone-trial.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale")
    stale_task = tmp_path / "_report" / "tasks" / "build-gone.html"
    stale_task.parent.mkdir(parents=True)
    stale_task.write_text("stale")
    stale_file = (
        tmp_path / "_report" / "tasks" / "build-gone" / "tests" / "check.py.html"
    )
    stale_file.parent.mkdir(parents=True)
    stale_file.write_text("stale")

    index = write_report(tmp_path)

    page = tmp_path / "_report" / run_dir.name / "t1.html"
    assert index.is_file() and page.is_file()
    assert not stale.exists() and not stale.parent.exists()
    assert not stale_task.exists()
    assert not (tmp_path / "_report" / "tasks" / "build-gone").exists()
    html = index.read_text()
    assert "Findings" in html and "vector-config" in html
    # The baseline arm names itself and shows its fail fraction and rate bar.
    assert "<dt>baseline</dt>" in html
    assert "1/1 failed" in html
    assert 'class="rate failed"' in html
    # No Treatment runs: the comparison section says so rather than erroring.
    assert "No Treatment runs are retained." in html
    trial_html = page.read_text()
    assert "collection uses the legacy vectorizer" in trial_html
    assert "weval.json" in trial_html

    # The Task page shows the packaged definition and opens every Trial, and
    # each page names the Task with a link to it.
    task_page = tmp_path / "_report" / "tasks" / "build-x.html"
    task_html = task_page.read_text()
    assert "Build **semantic search**." in task_html
    assert "environment/WORKSPACE.md" in task_html
    assert "the collection configures a named vector" in task_html
    assert f"../{run_dir.name}/t1.html" in task_html
    assert 'href="_report/tasks/build-x.html"' in html
    assert 'href="../tasks/build-x.html"' in trial_html

    # Each text file gets a highlighted page, and each check links to the
    # line that defines it; a binary file keeps its raw link.
    check_page = tmp_path / "_report" / "tasks" / "build-x" / "tests" / "check.py.html"
    assert 'id="L-4"' in check_page.read_text()
    assert '<span class="k">def</span>' in check_page.read_text()
    assert 'href="build-x/tests/check.py.html#L-4">source</a>' in task_html
    assert f"../{run_dir.name}/task/environment/data.bin" in task_html


def test_an_earlier_task_version_leaves_the_index_for_the_task_page(tmp_path):
    def write_run(name: str, task_version: str, failed: str) -> None:
        trial_dir = tmp_path / name / "job" / "t1"
        trial_dir.mkdir(parents=True)
        record = {
            "status": "failed",
            "task": TASK,
            "prompt_variant": "default",
            "treatment": None,
            "fingerprints": {"task": task_version, "check": "c1"},
            "agent": {"name": "agent", "harness": "pi"},
            "checks": [
                {"name": failed, "required": True, "passed": False, "notes": "x"}
            ],
        }
        (trial_dir / "weval.json").write_text(json.dumps(record))

    write_run("20260101-000001__build__x__agent", "old000000000", "old-check")
    write_run("20260102-000001__build__x__agent", "new000000000", "new-check")

    index = write_report(tmp_path).read_text()

    assert "new-check" in index and "old-check" not in index
    assert (
        'href="_report/tasks/build-x.html#earlier-versions">1 earlier version, 1 run'
        in index
    )
    task_html = (tmp_path / "_report" / "tasks" / "build-x.html").read_text()
    earlier = task_html.split('<h2 id="earlier-versions">')
    assert len(earlier) == 2, "the earlier versions come last, in their own section"
    assert "old-check" in earlier[1] and "old-check" not in earlier[0]
    assert "task old00000 / check c1" in earlier[1]


def test_notes_show_with_their_version_check_and_trials_and_survive_a_rebuild(
    tmp_path,
):
    def write_run(name: str, task_version: str) -> None:
        trial_dir = tmp_path / name / "job" / "t1"
        trial_dir.mkdir(parents=True)
        record = {
            "status": "failed",
            "task": TASK,
            "prompt_variant": "default",
            "treatment": None,
            "fingerprints": {"task": task_version, "check": "c1"},
            "agent": {"name": "agent", "harness": "pi"},
            "checks": [
                {"name": "a-check", "required": True, "passed": False, "notes": "x"}
            ],
        }
        (trial_dir / "weval.json").write_text(json.dumps(record))

    write_run("20260101-000001__build__x__agent", "old000000000")
    write_run("20260102-000001__build__x__agent", "new000000000")
    notes = tmp_path / "_report/notes/build-x"
    (notes / "new000000000").mkdir(parents=True)
    (notes / "new000000000/why.md").write_text(
        "---\nauthor: claude-code  # or a person\ndate: 2026-10-28\n"
        "check: a-check\ntrials: [t1]\n---\nThe agent kept `WORD` on purpose.\n"
    )
    (notes / "old000000000").mkdir()
    (notes / "old000000000/task.md").write_text("Superseded by the new prompt.\n")

    index = write_report(tmp_path).read_text()
    write_report(tmp_path)

    # The check's note sits under its finding; the old version's stays off the index.
    assert "by claude-code, 2026-10-28" in index
    assert "kept <code>WORD</code> on purpose" in index
    assert "Superseded" not in index
    task_html = (tmp_path / "_report/tasks/build-x.html").read_text()
    current, earlier = task_html.split('<h2 id="earlier-versions">')
    assert "on <code>a-check</code>" in current and "Superseded" not in current
    assert "by unknown author" in earlier and "Superseded" in earlier
    for run in ("20260101-000001", "20260102-000001"):
        trial_html = next((tmp_path / "_report").glob(f"{run}*/t1.html")).read_text()
        assert ("on purpose" in trial_html) == (run == "20260102-000001")
    assert (notes / "new000000000/why.md").exists()


def test_a_label_links_its_steps_to_the_transcript():
    answers = {
        "model": "jev-1.14.0",
        "steps_model": "openai/gpt-6-luna",
        "decision_step": 2,
        "steps": [{"step": 1, "kind": "source", "why": "lists 4.24.x"}],
        "cause": {"choice": "followed_source", "confidence": 0.73},
        "answer_source": {"choice": "own-knowledge", "confidence": 0.5},
    }
    steps = [{"step_id": 1, "source": "user"}, {"step_id": 2, "source": "agent"}]

    note, transcript = _labels_note(answers), _transcript(steps)

    assert 'decision step <a href="#step-2">2</a>' in note
    assert 'relevant steps <a href="#step-1">1</a>' in note
    assert "cause <code>followed_source</code> (0.73)" in note
    assert 'id="step-1"' in transcript and 'id="step-2"' in transcript
