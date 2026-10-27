"""``weval report`` builds the Task catalog and run rows from retained files."""

import json
from pathlib import Path

from weval.report import write_report
from weval.report.collect import collect_runs, collect_tasks, compare_treatments

RUN = "20261020-120000__build__ecommerce-search@terse__pi-glm-5.3-flash"


def write_trial(run_dir: Path, name: str, record: dict | None, agent_steps: int = 0) -> None:
    trial = run_dir / "job" / name
    (trial / "agent").mkdir(parents=True)
    if record is not None:
        (trial / "weval.json").write_text(json.dumps(record))
    (trial / "result.json").write_text(json.dumps({"agent_execution": {
        "started_at": "2026-10-20T10:00:00Z", "finished_at": "2026-10-20T10:02:00Z",
    }}))
    steps = [{"source": "user", "message": "Build search."}] + [{"source": "agent", "message": "Done."}] * agent_steps
    (trial / "agent/trajectory.json").write_text(json.dumps({"steps": steps}))


def record(status: str, preferred_passed: bool, cost: float) -> dict:
    return {
        "status": status,
        "task": "tasks/build/ecommerce-search",
        "prompt_variant": "terse",
        "agent": {"name": "pi-glm-5.3-flash"},
        "checks": [
            {"name": "a", "required": True, "passed": status == "passed"},
            {"name": "b", "required": False, "passed": preferred_passed},
        ],
        "usage": {"n_input_tokens": 900, "n_output_tokens": 100, "cost_usd": cost},
    }


def write_task(repo: Path, check_source: str) -> Path:
    task = repo / "tasks/build/ecommerce-search"
    (task / "prompts").mkdir(parents=True)
    (task / "task.toml").write_text("[agent]\ntimeout_sec = 1200.0\n")
    (task / "instruction.md").write_text("Build search.\n")
    (task / "prompts/terse.md").write_text("Search.\n")
    (task / "check.py").write_text(check_source)
    page = repo / "docs/tasks/build/ecommerce-search.md"
    page.parent.mkdir(parents=True)
    page.write_text("---\nmotivation: >\n  Can an agent\n  build search?\n---\n\n# build/ecommerce-search\n\n"
                    "The workspace holds\na `Product` catalog.\n\n## Checks\n")
    return repo / "tasks"


CHECKS = '''
def a(snapshot):
    """Products are ingested."""

def b(snapshot):
    """Queries are hybrid."""

def c(snapshot):
    """The terse prompt is answered."""

REQUIRED = [a]
PREFERRED = [b]
PROMPT_VARIANT_REQUIRED = {"default": [], "terse": [c]}
PROMPT_VARIANT_PREFERRED = {"default": [], "terse": []}
'''


def test_run_row_counts_scored_trials_and_averages_usage(tmp_path):
    run_dir = tmp_path / RUN
    write_trial(run_dir, "t1", record("passed", preferred_passed=True, cost=0.1), agent_steps=4)
    write_trial(run_dir, "t2", record("failed", preferred_passed=False, cost=0.3), agent_steps=6)
    write_trial(run_dir, "t3", record("non-result", preferred_passed=True, cost=0.2), agent_steps=5)
    (run_dir / "job/config.json").write_text(json.dumps({"environment": {"type": "docker"}}))

    [run] = collect_runs(tmp_path)

    assert (run.task, run.prompt_variant, run.agent, run.environment) == (
        "tasks/build/ecommerce-search", "terse", "pi-glm-5.3-flash", "local",
    )
    # The non-result counts toward neither score.
    assert [t.status for t in run.scored] == ["passed", "failed"]
    assert [t.preferred_passed for t in run.scored] == [True, False]
    assert [t.failed_required for t in run.scored] == [[], ["a"]]
    assert run.mean("cost_usd") == 0.2
    assert (run.mean("tokens"), run.mean("turns"), run.mean("duration_s")) == (1000, 5, 120)


def test_run_without_records_is_listed_from_its_name(tmp_path):
    run_dir = tmp_path / RUN
    write_trial(run_dir, "t1", None)

    [run] = collect_runs(tmp_path)

    assert (run.task, run.prompt_variant, run.agent) == (
        "tasks/build/ecommerce-search", "terse", "pi-glm-5.3-flash",
    )
    assert [t.status for t in run.trials] == ["unrecorded"]
    assert run.scored == []


def test_treatment_run_without_records_is_listed_from_its_name(tmp_path):
    run_dir = tmp_path / f"{RUN}+weaviate-docs"
    write_trial(run_dir, "t1", None)

    [run] = collect_runs(tmp_path)

    assert (run.agent, run.treatment) == ("pi-glm-5.3-flash", "weaviate-docs")


def test_treatment_runs_are_paired_with_baseline_runs_of_the_same_agent(tmp_path):
    other_agent = RUN.replace("pi-glm-5.3-flash", "claude-code-opus-5.5")
    for name in (RUN, RUN.replace("20261020-120000", "20261021-120000"), other_agent,
                 f"{RUN}+weaviate-docs", f"{other_agent}+weaviate-docs", f"{RUN}+other"):
        write_trial(tmp_path / name, "t1", None)

    comparisons = compare_treatments(collect_runs(tmp_path))

    assert [(c.treatment, c.agent, [r.path.name for r in c.baseline], [r.path.name for r in c.treated])
            for c in comparisons] == [
        ("other", "pi-glm-5.3-flash", [RUN.replace("20261020-120000", "20261021-120000"), RUN], [f"{RUN}+other"]),
        ("weaviate-docs", "claude-code-opus-5.5", [other_agent], [f"{other_agent}+weaviate-docs"]),
        ("weaviate-docs", "pi-glm-5.3-flash",
         [RUN.replace("20261020-120000", "20261021-120000"), RUN], [f"{RUN}+weaviate-docs"]),
    ]


def test_treatment_without_a_baseline_run_has_an_empty_baseline(tmp_path):
    write_trial(tmp_path / f"{RUN}+weaviate-docs", "t1", None)

    [comparison] = compare_treatments(collect_runs(tmp_path))

    assert comparison.baseline == []


def test_task_definition_reads_prompts_checks_and_page(tmp_path):
    [task] = collect_tasks(write_task(tmp_path, CHECKS))

    assert task.path == "tasks/build/ecommerce-search"
    assert task.motivation == "Can an agent build search?"
    assert task.summary == "The workspace holds a `Product` catalog."
    assert list(task.prompts) == ["default", "terse"]
    assert [(c.id, c.required) for c in task.checks_for("default")] == [("a", True), ("b", False)]
    assert [(c.id, c.description) for c in task.checks_for("terse")][-1] == ("c", "The terse prompt is answered.")
    assert task.config["agent"]["timeout_sec"] == 1200.0


def test_task_toml_metadata_takes_the_place_of_the_page(tmp_path):
    tasks_dir = write_task(tmp_path, CHECKS)
    task_toml = tasks_dir / "build/ecommerce-search/task.toml"
    task_toml.write_text('[metadata]\nmotivation = """\nCan an agent\nsearch?"""\n' + task_toml.read_text())

    [task] = collect_tasks(tasks_dir)

    assert (task.motivation, task.summary) == ("Can an agent search?", "")


def test_broken_check_module_is_reported_on_its_task(tmp_path):
    [task] = collect_tasks(write_task(tmp_path, "import missing_module\n"))

    assert task.checks == []
    assert "missing_module" in task.check_error


def test_site_links_catalog_results_and_trial_pages(tmp_path):
    tasks_dir = write_task(tmp_path / "repo", CHECKS)
    outputs = tmp_path / "outputs"
    write_trial(outputs / RUN, "t1", record("passed", preferred_passed=True, cost=0.1), agent_steps=1)
    write_trial(outputs / RUN, "t2", record("failed", preferred_passed=False, cost=0.3), agent_steps=1)
    stale = outputs / "_report/20260101-000000__gone__run__x/t9.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("")

    index = write_report(outputs, tasks_dir, tmp_path / "repo/agents.toml")

    page = index.read_text()
    results_link = ("#tab=results&amp;task=tasks/build/ecommerce-search&amp;variant=terse"
                    "&amp;agent=pi-glm-5.3-flash&amp;treatment=baseline")
    # The terse row's latest-run cell: 1 of 2 scored Trials passed, and check a failed once.
    assert f'<a class="chip partial" href="{results_link}"' in page
    assert '<span class="failed-required">a</span>' in page
    assert page.count('<td data-sort="0.5" class="num') == 2 and page.count(">1/2</td>") == 2
    assert f'href="_report/{RUN}/t1.html"' in page

    trial_page = (outputs / f"_report/{RUN}/t2.html").read_text()
    assert f'href="../../{RUN}/job/t2/weval.json"' in trial_page
    assert '<span class="chip fail">failed</span></td><td class="mono">a</td>' in trial_page
    assert "Done." in trial_page
    assert not stale.parent.exists()


def test_treatment_runs_are_compared_not_shown_as_the_latest_result(tmp_path):
    tasks_dir = write_task(tmp_path / "repo", CHECKS)
    outputs = tmp_path / "outputs"
    write_trial(outputs / RUN, "t1", record("passed", preferred_passed=True, cost=0.4))
    # Newer than the baseline, so it would be the catalog's latest run if Treatments counted.
    treated = RUN.replace("20261020-120000", "20261021-120000") + "+weaviate-docs"
    write_trial(outputs / treated, "t1", {**record("failed", preferred_passed=True, cost=0.3),
                                          "treatment": "weaviate-docs"})

    page = write_report(outputs, tasks_dir, tmp_path / "repo/agents.toml").read_text()

    assert '<a class="chip pass" href="#tab=results&amp;task=tasks/build/ecommerce-search' in page
    assert 'data-treatment="weaviate-docs"' in page and 'data-treatment="baseline"' in page
    treatments = page[page.index('<section class="tab" id="treatments"'):]
    assert '<td data-sort="1.0"' in treatments and '<td data-sort="0.0"' in treatments
    assert '0.300 <span class="note">-25%</span>' in treatments
