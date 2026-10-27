"""The report's view-model and page writing: failure groups carry per-arm
counts computed from records alone, saved judgments attach as annotations with
provenance, Task reliability counts what erodes trust, and ``write_report``
renders a retained run offline, removing stale Trial pages.
"""

import json
from pathlib import Path

from weval.collect import Comparison, RunSummary, TrialSummary
from weval.report import write_report
from weval.report.findings import failure_groups, task_reliability
from weval.report.pages import _block_markdown

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


def make_run(tmp_path: Path, name: str, treatment: str, trials) -> RunSummary:
    base = tmp_path / name
    return RunSummary(
        path=base,
        date=None,
        task=TASK,
        prompt_variant="default",
        treatment=treatment,
        agent="agent",
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
    assert [t.path.name for _, t in groups["vector-config"].arm_trials["skills"]] == [
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


def test_saved_judgments_attach_and_order_the_groups(tmp_path):
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
        TASK, "default", "agent", "skills", baseline=[baseline], treated=[treated]
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
    groups = failure_groups(
        [baseline, treated], [analysed(comparison, [pattern], rule)]
    )

    # Weaviate gap (the analyst's class) orders before agent gap (the rule's).
    assert [g.check for g in groups] == ["vector-config", "other-check"]
    assert groups[0].proposed_class == "Weaviate gap"
    assert groups[0].patterns[0]["model"] == "analyst-model"
    # No analyst pattern covers other-check: the rule's agreed class stands in.
    assert groups[1].proposed_class == "agent gap"
    assert groups[1].proposals == [rule[1]]


def test_disagreeing_judges_leave_a_group_unclassified(tmp_path):
    run = make_run(
        tmp_path,
        "20260101-000001__build__x__agent",
        "",
        [("t1", "failed", ["vector-config"])],
    )
    comparison = Comparison(
        TASK, "default", "agent", "skills", baseline=[run], treated=[]
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


def test_task_reliability_counts_what_erodes_trust(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "build-x-oracle-snapshot.json").write_text("{}")
    mixed = make_run(
        tmp_path,
        "20260101-000001__build__x__agent",
        "",
        [("t1", "passed"), ("t2", "failed", ["vector-config"]), ("t3", "non-result")],
    )
    comparison = Comparison(
        TASK, "default", "agent", "skills", baseline=[mixed], treated=[]
    )
    rule = [
        {"trial": "t2", "check": "vector-config", "class": "scorer bug", "reason": "x"}
    ]
    (row,) = task_reliability([mixed], [analysed(comparison, [], rule)], fixtures)

    assert (row.passed, row.scored) == (1, 2)
    assert row.non_results == 1
    assert row.mixed_runs == 1
    assert row.scorer_flags == 1
    assert row.calibrated


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
    stale = tmp_path / "_report" / "gone-run" / "gone-trial.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale")

    index = write_report(tmp_path)

    page = tmp_path / "_report" / run_dir.name / "t1.html"
    assert index.is_file() and page.is_file()
    assert not stale.exists() and not stale.parent.exists()
    html = index.read_text()
    assert "Findings" in html and "vector-config" in html
    # The baseline arm names itself and shows its fail fraction and waffle.
    assert "<dt>baseline</dt>" in html
    assert "1/1 failed" in html
    assert 'class="check-failed"' in html
    # No Treatment runs: the comparison section says so rather than erroring.
    assert "No Treatment runs are retained." in html
    trial_html = page.read_text()
    assert "collection uses the legacy vectorizer" in trial_html
    assert "weval.json" in trial_html
