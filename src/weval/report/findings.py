"""Group retained failures into findings and rate each Task's reliability.

The skeleton of a finding is deterministic: a ``FailureGroup`` is one check of
one Task and prompt variant, with per-arm fail counts computed from the
retained ``weval.json`` records alone, so the findings section is structurally
true even where nothing has been analysed. Saved judgments attach to that
skeleton as annotations with provenance: the analyst's patterns, the rule's
proposals, their disagreements, and Jev's answer-source labels. Nothing here
calls an LLM; analyses and labels are read as saved.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from weval import labels
from weval.collect import Comparison, RunSummary, TrialSummary

# Findings reading order: who must act. Weaviate gaps go to the product and
# docs owners, agent gaps to Treatment authors, Task defects and scorer bugs
# to weval itself; unclassified failures need a person, and infrastructure
# failures are non-findings listed last.
CLASS_ORDER = (
    "Weaviate gap",
    "agent gap",
    "Task defect",
    "scorer bug",
    "unclassified",
    "infrastructure failure",
)
BASELINE = "baseline"
# Classes that blame weval rather than the agent or Weaviate.
SCORER_CLASSES = ("scorer bug", "Task defect")


@dataclass
class FailureGroup:
    """One failed check of one Task and prompt variant, across every arm.

    ``arms`` maps each ``(agent, arm)`` pair, where the arm is ``baseline``
    or the Treatment name, to ``(failing, scored)`` Trial counts, so no count
    pools different Agents; ``arm_trials`` maps the same pairs to their
    scored Trials with their runs. Both are ordered by Agent, baseline first
    within each. ``failing`` lists the scored
    Trials that failed the check, with their runs, newest first.
    ``patterns`` holds the analyst patterns covering the check (each with its
    ``model`` and ``treatment`` added), ``proposals`` the rule's per-Trial
    classifications, ``disputed`` the (trial, analyst class, rule class)
    disagreements, and ``sources`` maps each failing Trial's directory name to
    its saved Jev answer-source label as ``(choice, confidence)``.
    """

    task: str
    prompt_variant: str
    check: str
    required: bool
    description: str = ""
    arms: dict[tuple[str, str], tuple[int, int]] = field(default_factory=dict)
    arm_trials: dict[tuple[str, str], list[tuple[RunSummary, TrialSummary]]] = field(
        default_factory=dict
    )
    failing: list[tuple[RunSummary, TrialSummary]] = field(default_factory=list)
    patterns: list[dict] = field(default_factory=list)
    proposals: list[dict] = field(default_factory=list)
    disputed: list[dict] = field(default_factory=list)
    sources: dict[str, tuple[str, float]] = field(default_factory=dict)

    @property
    def proposed_class(self) -> str:
        """The class the group presents first: the analyst's where one
        pattern covers the check, else the rule's where its proposals agree,
        else ``unclassified``. Always a proposal, never a verdict."""
        analyst = {p["class"] for p in self.patterns}
        if len(analyst) == 1:
            return next(iter(analyst))
        rule = {p["class"] for p in self.proposals}
        if not analyst and len(rule) == 1:
            return next(iter(rule))
        return "unclassified"


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
    """How far one Task and prompt variant's numbers can be trusted.

    ``runs`` is every retained run, newest first, and ``scored`` and
    ``passed`` count their Trials; ``arms`` splits the same runs by arm,
    baseline first. ``calibrated`` says an Oracle snapshot fixture exists in
    ``tests/``.
    """

    task: str
    prompt_variant: str
    runs: list[RunSummary]
    scored: int
    passed: int
    calibrated: bool
    arms: list[ArmReliability]


def failure_groups(
    runs: list[RunSummary], analyses: list[tuple[Comparison, dict]]
) -> list[FailureGroup]:
    """Every failed check across ``runs``, grouped and annotated from
    ``analyses`` (each Comparison with its saved ``analysis.analyse`` result),
    ordered by proposed class (``CLASS_ORDER``), required first, most failing
    Trials first."""
    # Keyed by (task, prompt variant, agent, arm).
    scored_by_arm: dict[tuple[str, str, str, str], list] = {}
    for run in runs:
        arm = run.treatment or BASELINE
        key = (run.task, run.prompt_variant, run.agent, arm)
        scored_by_arm.setdefault(key, []).extend((run, trial) for trial in run.scored)

    groups: dict[tuple[str, str, str], FailureGroup] = {}
    fail_counts: dict[tuple[str, str, str], Counter] = {}
    label_cache: dict[Path, dict] = {}
    for (task, prompt_variant, agent, arm), pairs in scored_by_arm.items():
        for run, trial in pairs:
            for check, required in [(c, True) for c in trial.failed_required] + [
                (c, False) for c in trial.failed_preferred
            ]:
                key = (task, prompt_variant, check)
                group = groups.setdefault(
                    key,
                    FailureGroup(
                        task=task,
                        prompt_variant=prompt_variant,
                        check=check,
                        required=required,
                        description=_description(trial, check),
                    ),
                )
                fail_counts.setdefault(key, Counter())[agent, arm] += 1
                group.failing.append((run, trial))
                source = _answer_source(trial, check, label_cache)
                if source:
                    group.sources[trial.path.name] = source
    # Every Agent and arm of the group's Task and prompt variant gets a
    # count, so a check failing in one arm still shows the others' 0 of N.
    for key, group in groups.items():
        group.arm_trials = _baseline_first(
            {
                (agent, arm): pairs
                for (task, variant, agent, arm), pairs in scored_by_arm.items()
                if (task, variant) == key[:2]
            }
        )
        group.arms = {
            agent_arm: (fail_counts[key][agent_arm], len(pairs))
            for agent_arm, pairs in group.arm_trials.items()
        }

    for comparison, found in analyses:
        for pattern in ((found.get("analysis") or {}).get("patterns")) or []:
            for check in pattern["checks"]:
                group = groups.get((comparison.task, comparison.prompt_variant, check))
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
                group = groups.get(
                    (comparison.task, comparison.prompt_variant, row["check"])
                )
                if group is not None and row not in getattr(group, name):
                    getattr(group, name).append(row)

    def order(group: FailureGroup) -> tuple:
        return (
            CLASS_ORDER.index(group.proposed_class),
            not group.required,
            -max((failed for failed, _ in group.arms.values()), default=0),
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
    """One ``TaskReliability`` per Task and prompt variant in ``runs``,
    sorted by Task path."""
    by_task: dict[tuple[str, str], list[RunSummary]] = {}
    for run in runs:
        by_task.setdefault((run.task, run.prompt_variant), []).append(run)

    # Keyed by (task, prompt variant, arm). Rule proposals are per Trial and
    # can repeat when two comparisons share a baseline, so they are collected
    # as a set; each analyst pattern belongs to one comparison.
    flags: Counter = Counter()
    rule_flags: set[tuple[str, str, str, str, str]] = set()
    for comparison, found in analyses:
        key = (comparison.task, comparison.prompt_variant)
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
                flags[*key, arm] += 1
        for row in found["rule"]:
            if row["class"] in SCORER_CLASSES and row["trial"] in arm_of:
                rule_flags.add((*key, arm_of[row["trial"]], row["trial"], row["check"]))
    for task, prompt_variant, arm, _, _ in rule_flags:
        flags[task, prompt_variant, arm] += 1

    rows = []
    for (task, prompt_variant), task_runs in sorted(by_task.items()):
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
                scorer_flags=flags[task, prompt_variant, arm],
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
                prompt_variant=prompt_variant,
                runs=task_runs,
                scored=sum(arm.scored for arm in arms),
                passed=sum(arm.passed for arm in arms),
                calibrated=fixture.is_file(),
                arms=arms,
            )
        )
    return rows


def _baseline_first[V](arms: dict[tuple[str, str], V]) -> dict[tuple[str, str], V]:
    """``arms`` keyed by ``(agent, arm)``, ordered by Agent with the baseline
    first within each."""
    ordered = sorted(
        arms.items(), key=lambda item: (item[0][0], item[0][1] != BASELINE, item[0][1])
    )
    return dict(ordered)


def _description(trial: TrialSummary, check: str) -> str:
    for row in (trial.record or {}).get("checks") or []:
        if row["name"] == check:
            return row.get("description") or ""
    return ""


def _answer_source(
    trial: TrialSummary, check: str, cache: dict[Path, dict]
) -> tuple[str, float] | None:
    """The saved Jev answer-source label for one failed check, if any."""
    if trial.path not in cache:
        checks = (trial.record or {}).get("checks") or []
        cache[trial.path] = labels.label(trial.path, checks, call=False)["labels"]
    answers = cache[trial.path].get(check)
    if not answers:
        return None
    source = answers["answer_source"]
    return str(source["choice"]), source["confidence"]
