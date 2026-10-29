"""Group retained failures into findings and rate each Task's reliability.

The skeleton of a finding is deterministic: a ``FailureGroup`` is one check of
one Task, with per-arm fail counts computed from the
retained ``weval.json`` records alone, so the findings section is structurally
true even where nothing has been analysed. Saved judgments attach to that
skeleton as annotations with provenance: the analyst's patterns, the rule's
proposals, their disagreements, and Jev's labels. Nothing here
calls an LLM; analyses and labels are read as saved.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from weval import labels
from weval.collect import Comparison, RunSummary, TrialSummary
from weval.report.notes import Note

BASELINE = "baseline"
# Classes that blame weval rather than the agent or Weaviate.
SCORER_CLASSES = ("scorer bug", "Task defect")


@dataclass
class FailureGroup:
    """One failed check of one Task, across every arm.

    ``arms`` maps each arm, ``baseline`` or the Treatment name, to
    ``(failing, scored)`` Trial counts across every Agent that ran it;
    ``arm_trials`` maps the same arms to their scored Trials with their runs,
    and ``failing_agents`` to the Agents with a failing Trial there, sorted.
    All three list the baseline first. ``failing`` lists the scored Trials
    that failed the check, with their runs, newest first.
    ``patterns`` holds the analyst patterns covering the check (each with its
    ``model`` and ``treatment`` added), ``proposals`` the rule's per-Trial
    classifications, ``disputed`` the (trial, analyst class, rule class)
    disagreements, and ``trial_labels`` maps each failing Trial's directory
    name to its saved labels for the check (``labels.label``). ``notes``
    holds the notes written about the check, which ``failure_groups`` leaves
    for the caller to attach.
    """

    task: str
    check: str
    required: bool
    description: str = ""
    arms: dict[str, tuple[int, int]] = field(default_factory=dict)
    arm_trials: dict[str, list[tuple[RunSummary, TrialSummary]]] = field(
        default_factory=dict
    )
    failing_agents: dict[str, list[str]] = field(default_factory=dict)
    failing: list[tuple[RunSummary, TrialSummary]] = field(default_factory=list)
    patterns: list[dict] = field(default_factory=list)
    proposals: list[dict] = field(default_factory=list)
    disputed: list[dict] = field(default_factory=list)
    trial_labels: dict[str, dict] = field(default_factory=dict)
    notes: list[Note] = field(default_factory=list)

    def headline(self) -> tuple[str, int, int]:
        """The arm whose failure rate leads the finding, with its
        ``(failing, scored)`` counts: the baseline when the check failed
        there, since a Treatment is an intervention, else the Treatment arm
        that failed it at the highest rate."""
        failed, scored = self.arms.get(BASELINE, (0, 0))
        if failed:
            return BASELINE, failed, scored
        return max(
            ((arm, f, s) for arm, (f, s) in self.arms.items() if f),
            key=lambda item: (item[1] / item[2], item[1]),
        )


@dataclass
class ArmReliability:
    """One arm of a Task's reliability, pooled across Agents.

    ``arm`` is ``baseline`` or the Treatment name, and ``runs`` its retained
    runs, newest first. ``non_results`` counts Trials with no scored outcome;
    ``mixed_runs`` counts runs whose scored Trials both pass and fail, which
    at identical settings is either real discrimination or flakiness;
    ``scorer_flags`` counts analyst patterns and rule proposals that class a
    failure in this arm as a scorer bug or Task defect. An analyst pattern
    citing Trials of both arms counts once in each.
    """

    arm: str
    runs: list[RunSummary]
    scored: int
    passed: int
    non_results: int
    mixed_runs: int
    scorer_flags: int


@dataclass
class TaskReliability:
    """How far one Task's numbers can be trusted.

    ``runs`` is every retained run, newest first, and ``scored`` and
    ``passed`` count their Trials; ``arms`` splits the same runs by arm,
    baseline first. ``calibrated`` says an Oracle snapshot fixture exists in
    ``tests/``.
    """

    task: str
    runs: list[RunSummary]
    scored: int
    passed: int
    calibrated: bool
    arms: list[ArmReliability]

    def definition(self) -> RunSummary:
        """The run whose package shows the Task's definition: the newest
        baseline run, since a Treatment can replace the prompt, or the newest
        run when no baseline ran."""
        return next((run for run in self.runs if not run.treatment), self.runs[0])


def failure_groups(
    runs: list[RunSummary], analyses: list[tuple[Comparison, dict]]
) -> list[FailureGroup]:
    """Every failed check across ``runs``, grouped and annotated from
    ``analyses`` (each Comparison with its saved ``analysis.analyse`` result),
    required first, then by the failure rate of each group's ``headline`` arm,
    baseline failures before Treatment-only ones, then by failing count."""
    # Keyed by (task, arm).
    scored_by_arm: dict[tuple[str, str], list] = {}
    for run in runs:
        arm = run.treatment or BASELINE
        key = (run.task, arm)
        scored_by_arm.setdefault(key, []).extend((run, trial) for trial in run.scored)

    groups: dict[tuple[str, str], FailureGroup] = {}
    fail_counts: dict[tuple[str, str], Counter] = {}
    label_cache: dict[Path, dict] = {}
    for (task, arm), pairs in scored_by_arm.items():
        for run, trial in pairs:
            for check, required in [(c, True) for c in trial.failed_required] + [
                (c, False) for c in trial.failed_preferred
            ]:
                key = (task, check)
                group = groups.setdefault(
                    key,
                    FailureGroup(
                        task=task,
                        check=check,
                        required=required,
                        description=_description(trial, check),
                    ),
                )
                fail_counts.setdefault(key, Counter())[arm] += 1
                group.failing_agents.setdefault(arm, []).append(run.agent)
                group.failing.append((run, trial))
                answers = _labels(trial, check, label_cache)
                if answers:
                    group.trial_labels[trial.path.name] = answers
    # Every arm of the group's Task gets a count, so a
    # check failing in one arm still shows the others' 0 of N.
    for key, group in groups.items():
        group.arm_trials = _baseline_first(
            {
                arm: pairs
                for (task, arm), pairs in scored_by_arm.items()
                if task == key[0]
            }
        )
        group.arms = {
            arm: (fail_counts[key][arm], len(pairs))
            for arm, pairs in group.arm_trials.items()
        }
        group.failing_agents = {
            arm: sorted(set(group.failing_agents.get(arm, [])))
            for arm in group.arm_trials
        }

    for comparison, found in analyses:
        for pattern in ((found.get("analysis") or {}).get("patterns")) or []:
            for check in pattern["checks"]:
                group = groups.get((comparison.task, check))
                if group is not None:
                    group.patterns.append(
                        {
                            **pattern,
                            "model": found.get("model"),
                            "treatment": comparison.treatment,
                        }
                    )
        for name, rows in (
            ("proposals", found["rule"]),
            ("disputed", found["disagreements"]),
        ):
            for row in rows:
                group = groups.get((comparison.task, row["check"]))
                if group is not None and row not in getattr(group, name):
                    getattr(group, name).append(row)

    def order(group: FailureGroup) -> tuple:
        arm, failed, scored = group.headline()
        return (
            not group.required,
            arm != BASELINE,
            -failed / scored,
            -failed,
            group.task,
            group.check,
        )

    for group in groups.values():
        group.failing.sort(key=lambda pair: pair[0].path.name, reverse=True)
    return sorted(groups.values(), key=order)


def task_reliability(
    runs: list[RunSummary],
    analyses: list[tuple[Comparison, dict]],
    fixtures_dir: Path,
) -> list[TaskReliability]:
    """One ``TaskReliability`` per Task in ``runs``, sorted by Task path."""
    by_task: dict[str, list[RunSummary]] = {}
    for run in runs:
        by_task.setdefault(run.task, []).append(run)

    # Keyed by (task, arm). Rule proposals are per Trial and
    # can repeat when two comparisons share a baseline, so they are collected
    # as a set; each analyst pattern belongs to one comparison.
    flags: Counter = Counter()
    rule_flags: set[tuple[str, str, str, str]] = set()
    for comparison, found in analyses:
        arm_of = {
            trial.path.name: run.treatment or BASELINE
            for run in [*comparison.baseline, *comparison.treated]
            for trial in run.trials
        }
        for pattern in ((found.get("analysis") or {}).get("patterns")) or []:
            if pattern["class"] not in SCORER_CLASSES:
                continue
            arms = {arm_of[t] for t in pattern.get("trials") or [] if t in arm_of}
            for arm in arms or {BASELINE, comparison.treatment}:
                flags[comparison.task, arm] += 1
        for row in found["rule"]:
            if row["class"] in SCORER_CLASSES and row["trial"] in arm_of:
                rule_flags.add(
                    (comparison.task, arm_of[row["trial"]], row["trial"], row["check"])
                )
    for task, arm, _, _ in rule_flags:
        flags[task, arm] += 1

    rows = []
    for task, task_runs in sorted(by_task.items()):
        by_arm: dict[str, list[RunSummary]] = {}
        for run in task_runs:
            by_arm.setdefault(run.treatment or BASELINE, []).append(run)
        arms = [
            ArmReliability(
                arm=arm,
                runs=arm_runs,
                scored=sum(len(run.scored) for run in arm_runs),
                passed=sum(
                    t.status == "passed" for run in arm_runs for t in run.scored
                ),
                non_results=sum(len(run.trials) - len(run.scored) for run in arm_runs),
                mixed_runs=sum(
                    "passed" in statuses and len(statuses) > 1
                    for statuses in ({t.status for t in run.scored} for run in arm_runs)
                ),
                scorer_flags=flags[task, arm],
            )
            for arm, arm_runs in sorted(
                by_arm.items(), key=lambda item: (item[0] != BASELINE, item[0])
            )
        ]
        fixture = (
            fixtures_dir
            / f"{task.removeprefix('tasks/').replace('/', '-')}-oracle-snapshot.json"
        )
        rows.append(
            TaskReliability(
                task=task,
                runs=task_runs,
                scored=sum(arm.scored for arm in arms),
                passed=sum(arm.passed for arm in arms),
                calibrated=fixture.is_file(),
                arms=arms,
            )
        )
    return rows


def _baseline_first[V](arms: dict[str, V]) -> dict[str, V]:
    """``arms`` with the baseline first, then Treatments by name."""
    return dict(sorted(arms.items(), key=lambda item: (item[0] != BASELINE, item[0])))


def _description(trial: TrialSummary, check: str) -> str:
    for row in (trial.record or {}).get("checks") or []:
        if row["name"] == check:
            return row.get("description") or ""
    return ""


def _labels(trial: TrialSummary, check: str, cache: dict[Path, dict]) -> dict | None:
    """The saved labels for one failed check, if any."""
    if trial.path not in cache:
        checks = (trial.record or {}).get("checks") or []
        cache[trial.path] = labels.label(trial.path, checks, call=False)["labels"]
    return cache[trial.path].get(check)
