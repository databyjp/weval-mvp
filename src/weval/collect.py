"""Read retained runs under ``experiment-outputs/`` into summaries.

The summaries serve ``weval analyse`` and any later presentation of results.
Everything here only reads files; retained runs are never modified.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median

# Statuses whose reward the verifier recorded; see docs/reference.md.
SCORED = ("passed", "failed", "timed-out")


@dataclass
class TrialSummary:
    """One Trial's outcome and usage, as read from its retained files.

    ``status`` is ``weval.json``'s status, or ``unrecorded`` when the Trial
    has no ``weval.json``, in which case ``record`` is ``None``.
    ``preferred_passed`` is ``None`` when the Trial records no preferred
    checks. ``failed_required`` and ``failed_preferred`` list failed check
    IDs. Usage fields are ``None`` when not reported. ``uncached_input``
    is input tokens not read from the prompt cache (Harbor's and Claude
    Code's input counts include cache reads).
    """

    path: Path
    status: str
    record: dict | None = None
    preferred_passed: bool | None = None
    failed_required: list[str] = field(default_factory=list)
    failed_preferred: list[str] = field(default_factory=list)
    cost_usd: float | None = None
    tokens: int | None = None
    uncached_input: int | None = None
    turns: int | None = None
    duration_s: float | None = None


@dataclass
class RunSummary:
    """One run directory: the Trials one ``weval run`` invocation produced.

    ``task``, ``prompt_variant``, ``treatment``, ``agent``, and
    ``fingerprints`` come from the first Trial's ``weval.json``, or from the
    run directory name when no Trial has one. ``treatment`` is blank for a
    baseline run. ``fingerprints`` (docs/reference.md) is ``None`` for a run
    recorded before fingerprints existed.
    """

    path: Path
    date: datetime | None
    task: str
    prompt_variant: str
    treatment: str
    agent: str
    trials: list[TrialSummary]
    fingerprints: dict | None = None

    @property
    def scored(self) -> list[TrialSummary]:
        return [t for t in self.trials if t.status in SCORED]

    def mean(self, attribute: str) -> float | None:
        """Mean of a usage field over the Trials that report it."""
        return mean_usage(self.trials, attribute)


@dataclass
class AgentChange:
    """One Agent's Trials in both arms of a ``Comparison``.

    ``change`` compares the Agent's pass rates over scored Trials:
    ``helped`` or ``hurt`` when the Treatment arm's is higher or lower,
    ``unchanged`` when they are equal, and ``None`` when either arm has no
    scored Trial.
    """

    agent: str
    baseline: list[TrialSummary]
    treated: list[TrialSummary]

    @property
    def change(self) -> str | None:
        rates = []
        for trials in (self.baseline, self.treated):
            scored = [t for t in trials if t.status in SCORED]
            if not scored:
                return None
            rates.append(sum(t.status == "passed" for t in scored) / len(scored))
        if rates[1] == rates[0]:
            return "unchanged"
        return "helped" if rates[1] > rates[0] else "hurt"


@dataclass
class Comparison:
    """One Treatment against its baseline for one Task and prompt variant,
    across Agents.

    ``agents`` names, sorted, the Agents with runs in both arms, and
    ``baseline`` and ``treated`` hold only their runs, so both arms cover the
    same models; ``unpaired`` names the Agents with runs in one arm only.
    When no Agent ran both arms, ``agents`` and ``baseline`` are empty and
    ``treated`` holds every Treatment run. Both arms ran the same
    ``task_version`` and ``check_version``, and every ``treated`` run had the
    same ``treatment_version``; each is a fingerprint (docs/reference.md), or
    ``None`` for runs recorded without one, which are compared only with each
    other. Runs are newest first.
    """

    task: str
    prompt_variant: str
    treatment: str
    baseline: list[RunSummary]
    treated: list[RunSummary]
    agents: list[str] = field(default_factory=list)
    unpaired: list[str] = field(default_factory=list)
    task_version: str | None = None
    check_version: str | None = None
    treatment_version: str | None = None

    def by_agent(self) -> list[AgentChange]:
        """Each compared Agent's Trials, in ``agents`` order."""
        return [
            AgentChange(
                agent,
                [t for run in self.baseline if run.agent == agent for t in run.trials],
                [t for run in self.treated if run.agent == agent for t in run.trials],
            )
            for agent in self.agents
        ]


def collect_runs(outputs_dir: Path) -> list[RunSummary]:
    """Summarise every run directory under ``outputs_dir``, newest first."""
    run_dirs = [path for path in outputs_dir.iterdir() if (path / "job").is_dir()]
    return [summarise_run(run_dir) for run_dir in sorted(run_dirs, reverse=True)]


def compare_treatments(runs: list[RunSummary]) -> list[Comparison]:
    """One ``Comparison`` per Treatment version, Task, prompt variant, and
    Task and check versions with a Treatment run, sorted by those fields."""
    groups: dict[tuple, list[RunSummary]] = {}
    for run in runs:
        versions = run.fingerprints or {}
        key = (
            run.treatment,
            versions.get("treatment"),
            run.task,
            run.prompt_variant,
            versions.get("task"),
            versions.get("check"),
        )
        groups.setdefault(key, []).append(run)
    comparisons = []
    for key, treated in groups.items():
        (
            treatment,
            treatment_version,
            task,
            prompt_variant,
            task_version,
            check_version,
        ) = key
        if not treatment:
            continue
        baseline = groups.get(
            ("", None, task, prompt_variant, task_version, check_version), []
        )
        treated_agents = {run.agent for run in treated}
        baseline_agents = {run.agent for run in baseline}
        agents = sorted(treated_agents & baseline_agents)
        if agents:
            baseline = [run for run in baseline if run.agent in agents]
            treated = [run for run in treated if run.agent in agents]
        else:
            baseline = []
        comparisons.append(
            Comparison(
                task,
                prompt_variant,
                treatment,
                baseline=baseline,
                treated=treated,
                agents=agents,
                unpaired=sorted(treated_agents ^ baseline_agents),
                task_version=task_version,
                check_version=check_version,
                treatment_version=treatment_version,
            )
        )
    # Unversioned (None) sorts first.
    return sorted(
        comparisons,
        key=lambda c: tuple(
            v or ""
            for v in (
                c.treatment,
                c.task,
                c.prompt_variant,
                c.task_version,
                c.check_version,
                c.treatment_version,
            )
        ),
    )


def mean_usage(trials: list[TrialSummary], attribute: str) -> float | None:
    """Mean of a usage field over the ``trials`` that report it."""
    values = [
        getattr(t, attribute) for t in trials if getattr(t, attribute) is not None
    ]
    return mean(values) if values else None


def median_change(by_agent: list[AgentChange], attribute: str) -> float | None:
    """The median of ``agent_usage_changes``; ``None`` when no Agent gives a
    change. Agents are compared with themselves first, so one costly model
    does not set the result."""
    changes = agent_usage_changes(by_agent, attribute)
    return median(changes) if changes else None


def agent_usage_changes(by_agent: list[AgentChange], attribute: str) -> list[float]:
    """Each Agent's change in a usage field's mean, Treatment against
    baseline, as a fraction of the baseline mean. An Agent without figures in
    either arm, or with a zero baseline mean, gives no change. Only scored
    Trials count: a non-result's usage stops wherever its failure did."""
    changes = []
    for row in by_agent:
        treated = mean_usage([t for t in row.treated if t.status in SCORED], attribute)
        baseline = mean_usage(
            [t for t in row.baseline if t.status in SCORED], attribute
        )
        if treated is not None and baseline:
            changes.append((treated - baseline) / baseline)
    return changes


def summarise_run(run_dir: Path) -> RunSummary:
    trial_dirs = sorted(path for path in (run_dir / "job").iterdir() if path.is_dir())
    records = [_read_json(path / "weval.json") for path in trial_dirs]
    first = next((record for record in records if record), None)
    if first:
        task = first.get("task", "")
        prompt_variant = first.get("prompt_variant", "default")
        treatment = first.get("treatment") or ""
        agent = (first.get("agent") or {}).get("name", "")
        fingerprints = first.get("fingerprints")
    else:
        task, prompt_variant, agent, treatment = _parse_run_name(run_dir.name)
        fingerprints = None
    return RunSummary(
        path=run_dir,
        date=_parse_stamp(run_dir.name),
        task=task,
        prompt_variant=prompt_variant,
        treatment=treatment,
        agent=agent,
        trials=[
            summarise_trial(path, record) for path, record in zip(trial_dirs, records)
        ],
        fingerprints=fingerprints,
    )


def summarise_trial(trial_dir: Path, record: dict | None) -> TrialSummary:
    if record is None:
        return TrialSummary(path=trial_dir, status="unrecorded")

    checks = record.get("checks") or []
    preferred = [check["passed"] for check in checks if not check["required"]]
    usage = record.get("usage") or {}
    token_counts = [
        usage[key]
        for key in ("n_input_tokens", "n_output_tokens")
        if usage.get(key) is not None
    ]
    result = _read_json(trial_dir / "result.json") or {}
    trajectory = _read_json(trial_dir / "agent/trajectory.json")
    return TrialSummary(
        path=trial_dir,
        status=record["status"],
        record=record,
        preferred_passed=all(preferred) if preferred else None,
        failed_required=[
            c["name"] for c in checks if c["required"] and not c["passed"]
        ],
        failed_preferred=[
            c["name"] for c in checks if not c["required"] and not c["passed"]
        ],
        cost_usd=usage.get("cost_usd"),
        tokens=sum(token_counts) if token_counts else None,
        uncached_input=usage["n_input_tokens"] - (usage.get("n_cache_tokens") or 0)
        if usage.get("n_input_tokens") is not None
        else None,
        # A turn is one agent message in Harbor's trajectory, with or without tool calls.
        turns=sum(step.get("source") == "agent" for step in trajectory["steps"])
        if trajectory
        else None,
        duration_s=_duration_s(result.get("agent_execution")),
    )


def _duration_s(span: dict | None) -> float | None:
    if not span or not span.get("started_at") or not span.get("finished_at"):
        return None
    started, finished = (
        datetime.fromisoformat(span[key]) for key in ("started_at", "finished_at")
    )
    return (finished - started).total_seconds()


def _parse_stamp(run_name: str) -> datetime | None:
    try:
        return datetime.strptime(run_name[:15], "%Y%m%d-%H%M%S")
    except ValueError:
        return None


def _parse_run_name(run_name: str) -> tuple[str, str, str, str]:
    """Return ``(task, prompt_variant, agent, treatment)`` from ``run.py``'s
    run name, ``<stamp>__<stage>__<scenario>[@<prompt-variant>]__<agent>[+<treatment>]``;
    blanks when the name has another form."""
    parts = run_name.split("__")
    if len(parts) != 4:
        return "", "", "", ""
    _, stage, scenario, agent = parts
    scenario, _, prompt_variant = scenario.partition("@")
    agent, _, treatment = agent.partition("+")
    return f"tasks/{stage}/{scenario}", prompt_variant or "default", agent, treatment


def _read_json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.is_file() else None
