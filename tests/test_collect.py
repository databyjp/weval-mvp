"""Run summaries and Treatment pairing are read from retained files."""

import json
from pathlib import Path

from weval.collect import (
    collect_runs,
    compare_treatments,
    fisher_exact,
    wilson_interval,
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


def test_treatment_runs_are_paired_with_baseline_runs_of_the_same_agent(tmp_path):
    other_agent = RUN.replace("pi-glm-5.3-flash", "claude-code-opus-5.5")
    for name in (
        RUN,
        RUN.replace("20261020-120000", "20261021-120000"),
        other_agent,
        f"{RUN}+weaviate-docs",
        f"{other_agent}+weaviate-docs",
        f"{RUN}+other",
    ):
        write_trial(tmp_path / name, "t1", None)

    comparisons = compare_treatments(collect_runs(tmp_path))

    assert [
        (
            c.treatment,
            c.agent,
            [r.path.name for r in c.baseline],
            [r.path.name for r in c.treated],
        )
        for c in comparisons
    ] == [
        (
            "other",
            "pi-glm-5.3-flash",
            [RUN.replace("20261020-120000", "20261021-120000"), RUN],
            [f"{RUN}+other"],
        ),
        (
            "weaviate-docs",
            "claude-code-opus-5.5",
            [other_agent],
            [f"{other_agent}+weaviate-docs"],
        ),
        (
            "weaviate-docs",
            "pi-glm-5.3-flash",
            [RUN.replace("20261020-120000", "20261021-120000"), RUN],
            [f"{RUN}+weaviate-docs"],
        ),
    ]


def test_treatment_without_a_baseline_run_has_an_empty_baseline(tmp_path):
    write_trial(tmp_path / f"{RUN}+weaviate-docs", "t1", None)

    [comparison] = compare_treatments(collect_runs(tmp_path))

    assert comparison.baseline == []


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


def test_pass_rate_statistics_match_hand_computed_values():
    # 3/5 against 0/5: the observed split and its mirror each have probability 10/120.
    assert round(fisher_exact(3, 5, 0, 5), 4) == round(20 / 120, 4)
    # 5/5 against 0/7: the observed split is the only one as unlikely, C(12, 5) = 792.
    assert round(fisher_exact(5, 5, 0, 7), 6) == round(1 / 792, 6)
    assert round(fisher_exact(2, 4, 2, 4), 9) == 1.0
    assert [round(v, 3) for v in wilson_interval(3, 5)] == [0.231, 0.882]
    assert wilson_interval(0, 5)[0] == 0.0 and wilson_interval(5, 5)[1] == 1.0


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
