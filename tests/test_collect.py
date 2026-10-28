"""Run summaries and Treatment pairing are read from retained files."""

import json
from pathlib import Path

from weval.collect import (
    AgentChange,
    TrialSummary,
    collect_runs,
    compare_treatments,
)

RUN = "20261020-120000__build__ecommerce-search@terse__pi-glm-5.3-flash"


def write_trial(
    run_dir: Path, name: str, record: dict | None, agent_steps: int = 0
) -> None:
    trial = run_dir / "job" / name
    (trial / "agent").mkdir(parents=True)
    if record is not None:
        (trial / "weval.json").write_text(json.dumps(record))
    (trial / "result.json").write_text(
        json.dumps(
            {
                "agent_execution": {
                    "started_at": "2026-10-20T10:00:00Z",
                    "finished_at": "2026-10-20T10:02:00Z",
                }
            }
        )
    )
    steps = [{"source": "user", "message": "Build search."}] + [
        {"source": "agent", "message": "Done."}
    ] * agent_steps
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


def test_run_row_counts_scored_trials_and_averages_usage(tmp_path):
    run_dir = tmp_path / RUN
    write_trial(
        run_dir, "t1", record("passed", preferred_passed=True, cost=0.1), agent_steps=4
    )
    write_trial(
        run_dir, "t2", record("failed", preferred_passed=False, cost=0.3), agent_steps=6
    )
    write_trial(
        run_dir,
        "t3",
        record("non-result", preferred_passed=True, cost=0.2),
        agent_steps=5,
    )

    [run] = collect_runs(tmp_path)

    assert (run.task, run.prompt_variant, run.agent) == (
        "tasks/build/ecommerce-search",
        "terse",
        "pi-glm-5.3-flash",
    )
    # The non-result counts toward neither score.
    assert [t.status for t in run.scored] == ["passed", "failed"]
    assert [t.preferred_passed for t in run.scored] == [True, False]
    assert [t.failed_required for t in run.scored] == [[], ["a"]]
    assert run.mean("cost_usd") == 0.2
    assert (run.mean("tokens"), run.mean("turns"), run.mean("duration_s")) == (
        1000,
        5,
        120,
    )


def test_run_without_records_is_listed_from_its_name(tmp_path):
    run_dir = tmp_path / RUN
    write_trial(run_dir, "t1", None)

    [run] = collect_runs(tmp_path)

    assert (run.task, run.prompt_variant, run.agent) == (
        "tasks/build/ecommerce-search",
        "terse",
        "pi-glm-5.3-flash",
    )
    assert [t.status for t in run.trials] == ["unrecorded"]
    assert run.scored == []


def test_treatment_run_without_records_is_listed_from_its_name(tmp_path):
    run_dir = tmp_path / f"{RUN}+weaviate-docs"
    write_trial(run_dir, "t1", None)

    [run] = collect_runs(tmp_path)

    assert (run.agent, run.treatment) == ("pi-glm-5.3-flash", "weaviate-docs")


def test_a_comparison_spans_the_agents_that_ran_both_arms(tmp_path):
    opus = RUN.replace("pi-glm-5.3-flash", "claude-code-opus-5.5")
    haiku = RUN.replace("pi-glm-5.3-flash", "claude-code-haiku-5.5")
    gpt = RUN.replace("pi-glm-5.3-flash", "pi-gpt-6.1-terra")
    for name in (
        RUN,
        RUN.replace("20261020-120000", "20261021-120000"),
        opus,
        haiku,  # baseline only
        f"{RUN}+weaviate-docs",
        f"{opus}+weaviate-docs",
        f"{gpt}+weaviate-docs",  # Treatment only
        f"{RUN}+other",
    ):
        write_trial(tmp_path / name, "t1", None)

    comparisons = compare_treatments(collect_runs(tmp_path))

    assert [
        (
            c.treatment,
            c.agents,
            c.unpaired,
            [r.path.name for r in c.baseline],
            [r.path.name for r in c.treated],
        )
        for c in comparisons
    ] == [
        (
            "other",
            ["pi-glm-5.3-flash"],
            ["claude-code-haiku-5.5", "claude-code-opus-5.5"],
            [RUN.replace("20261020-120000", "20261021-120000"), RUN],
            [f"{RUN}+other"],
        ),
        # Haiku has no Treatment run and GPT no baseline run: neither arm
        # gets a model the other lacks.
        (
            "weaviate-docs",
            ["claude-code-opus-5.5", "pi-glm-5.3-flash"],
            ["claude-code-haiku-5.5", "pi-gpt-6.1-terra"],
            sorted(
                [RUN, RUN.replace("20261020-120000", "20261021-120000"), opus],
                reverse=True,
            ),
            sorted([f"{RUN}+weaviate-docs", f"{opus}+weaviate-docs"], reverse=True),
        ),
    ]


def test_an_agent_change_compares_its_pass_rates_in_the_two_arms():
    def trials(*statuses: str) -> list[TrialSummary]:
        return [
            TrialSummary(Path(f"t{i}"), status) for i, status in enumerate(statuses)
        ]

    def change(baseline: list, treated: list) -> str | None:
        return AgentChange("agent", baseline, treated).change

    assert change(trials("failed"), trials("passed")) == "helped"
    assert change(trials("passed"), trials("timed-out")) == "hurt"
    # A non-result is not scored: the rates are 1/1 and 1/1.
    assert change(trials("passed"), trials("passed", "non-result")) == "unchanged"
    assert change(trials("passed"), trials("non-result")) is None


def test_treatment_without_a_baseline_run_has_an_empty_baseline(tmp_path):
    write_trial(tmp_path / f"{RUN}+weaviate-docs", "t1", None)

    [comparison] = compare_treatments(collect_runs(tmp_path))

    assert comparison.baseline == []
    assert comparison.agents == []
    assert [r.path.name for r in comparison.treated] == [f"{RUN}+weaviate-docs"]


def test_treatment_runs_are_paired_only_with_baselines_of_the_same_task_and_check_versions(
    tmp_path,
):
    def versioned(
        treatment: str | None,
        task: str,
        check: str,
        treatment_version: str | None = None,
    ) -> dict:
        return {
            **record("passed", preferred_passed=True, cost=0.1),
            "treatment": treatment,
            "fingerprints": {
                "task": task,
                "check": check,
                "treatment": treatment_version,
            },
        }

    runs = {
        RUN: versioned(None, "task-v1", "check-v1"),
        RUN.replace("20261020", "20261021"): versioned(None, "task-v1", "check-v2"),
        RUN.replace("20261020", "20261022"): versioned(None, "task-v2", "check-v1"),
        RUN.replace(
            "20261020", "20261019"
        ): None,  # unversioned: recorded before fingerprints
        f"{RUN.replace('20261020', '20261023')}+weaviate-docs": versioned(
            "weaviate-docs", "task-v1", "check-v1", "docs-v1"
        ),
        f"{RUN.replace('20261020', '20261024')}+weaviate-docs": versioned(
            "weaviate-docs", "task-v1", "check-v1", "docs-v2"
        ),
        f"{RUN.replace('20261020', '20261018')}+weaviate-docs": None,
    }
    for name, weval_record in runs.items():
        write_trial(tmp_path / name, "t1", weval_record)

    comparisons = compare_treatments(collect_runs(tmp_path))

    assert [
        (
            c.treatment_version,
            c.task_version,
            c.check_version,
            [r.path.name[:8] for r in c.baseline],
            [r.path.name[:8] for r in c.treated],
        )
        for c in comparisons
    ] == [
        (None, None, None, ["20261019"], ["20261018"]),
        ("docs-v1", "task-v1", "check-v1", ["20261020"], ["20261023"]),
        ("docs-v2", "task-v1", "check-v1", ["20261020"], ["20261024"]),
    ]


def test_uncached_input_leaves_out_cache_reads(tmp_path):
    usage = {
        "n_input_tokens": 150_000,
        "n_cache_tokens": 120_000,
        "n_output_tokens": 3_000,
    }
    write_trial(
        tmp_path / RUN,
        "t1",
        {**record("passed", preferred_passed=True, cost=0.1), "usage": usage},
    )

    [run] = collect_runs(tmp_path)

    assert run.trials[0].uncached_input == 30_000
