"""Read the Task catalog, ``agents.toml``, and retained runs into report data.

Everything here only reads files. Retained runs under ``experiment-outputs/``
are never modified, and each Task's ``check.py`` is imported only to read its
check lists and docstrings.
"""

import importlib.util
import inspect
import json
import tomllib
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean

# Statuses whose reward the verifier recorded; see docs/reference.md.
SCORED = ("passed", "failed", "timed-out")
# Per-Trial files linked from the report, by label, relative to the Trial directory.
KEY_FILES = {
    "weval.json": "weval.json",
    "checks": "verifier/checks.json",
    "snapshot": "verifier/snapshot.json",
    "test output": "verifier/test-stdout.txt",
    "trajectory": "agent/trajectory.json",
    "submission": "artifacts/submission",
}
ENVIRONMENTS = {"modal": "Modal", "docker": "local"}


@dataclass
class TrialSummary:
    """One Trial's outcome and usage, as read from its retained files.

    ``status`` is ``weval.json``'s status, or ``unrecorded`` when the Trial
    has no ``weval.json``, in which case ``record`` is ``None``.
    ``preferred_passed`` is ``None`` when the Trial records no preferred
    checks. ``failed_required`` and ``failed_preferred`` list failed check
    IDs. Usage fields are ``None`` when not reported.
    """

    path: Path
    status: str
    record: dict | None = None
    preferred_passed: bool | None = None
    failed_required: list[str] = field(default_factory=list)
    failed_preferred: list[str] = field(default_factory=list)
    cost_usd: float | None = None
    tokens: int | None = None
    turns: int | None = None
    duration_s: float | None = None
    files: dict[str, Path] = field(default_factory=dict)


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
    environment: str
    trials: list[TrialSummary]
    fingerprints: dict | None = None

    @property
    def scored(self) -> list[TrialSummary]:
        return [t for t in self.trials if t.status in SCORED]

    def mean(self, attribute: str) -> float | None:
        """Mean of a usage field over the Trials that report it."""
        return mean_usage(self.trials, attribute)


@dataclass
class Comparison:
    """One Treatment against its baseline for one Task, prompt variant, and Agent.

    Both arms ran the same ``task_version`` and ``check_version``, and every
    ``treated`` run had the same ``treatment_version``; each is a fingerprint
    (docs/reference.md), or ``None`` for runs recorded without one, which are
    compared only with each other. ``baseline`` holds that combination's runs
    without a Treatment and ``treated`` its runs with ``treatment``, each
    newest first; ``baseline`` is empty when no such baseline run is retained.
    """

    task: str
    prompt_variant: str
    agent: str
    treatment: str
    baseline: list[RunSummary]
    treated: list[RunSummary]
    task_version: str | None = None
    check_version: str | None = None
    treatment_version: str | None = None


@dataclass
class CheckDefinition:
    """One check function that a Task's ``check.py`` scores.

    ``prompt_variant`` is ``None`` for a check scored under every prompt
    variant, or the one prompt variant whose list adds it.
    """

    id: str
    required: bool
    description: str
    prompt_variant: str | None = None


@dataclass
class TaskDefinition:
    """One Task directory, read as an agent and its verifier see it.

    ``path`` is ``tasks/<stage>/<scenario>``, the form ``weval.json`` records.
    ``prompts`` maps each prompt variant to its prompt; ``default`` is
    ``instruction.md``. ``motivation`` and ``summary`` come from
    ``task.toml``'s ``[metadata]``, or else from the Task page, and are blank
    without either. When ``check.py`` fails to import, ``checks`` is empty and
    ``check_error`` holds the exception line. ``expected`` is ``check.py``'s
    ``EXPECTED`` (docs/how-to/define-a-task.md), empty when it has none.
    """

    path: str
    directory: Path
    page: Path | None
    motivation: str
    summary: str
    prompts: dict[str, str]
    checks: list[CheckDefinition]
    check_error: str | None
    config: dict
    expected: dict = field(default_factory=dict)

    def checks_for(self, prompt_variant: str) -> list[CheckDefinition]:
        """The checks a Trial of ``prompt_variant`` is scored on."""
        return [c for c in self.checks if c.prompt_variant in (None, prompt_variant)]


def collect_runs(outputs_dir: Path) -> list[RunSummary]:
    """Summarise every run directory under ``outputs_dir``, newest first."""
    run_dirs = [path for path in outputs_dir.iterdir() if (path / "job").is_dir()]
    return [summarise_run(run_dir) for run_dir in sorted(run_dirs, reverse=True)]


def compare_treatments(runs: list[RunSummary]) -> list[Comparison]:
    """One ``Comparison`` per Treatment version, Task, prompt variant, Agent,
    and Task and check versions with a Treatment run, sorted by those fields."""
    groups: dict[tuple, list[RunSummary]] = {}
    for run in runs:
        versions = run.fingerprints or {}
        key = (run.treatment, versions.get("treatment"), run.task, run.prompt_variant, run.agent,
               versions.get("task"), versions.get("check"))
        groups.setdefault(key, []).append(run)
    comparisons = []
    for key, treated in groups.items():
        treatment, treatment_version, task, prompt_variant, agent, task_version, check_version = key
        if not treatment:
            continue
        baseline = groups.get(("", None, task, prompt_variant, agent, task_version, check_version), [])
        comparisons.append(Comparison(
            task, prompt_variant, agent, treatment, baseline=baseline, treated=treated,
            task_version=task_version, check_version=check_version, treatment_version=treatment_version,
        ))
    # Unversioned (None) sorts first.
    return sorted(comparisons, key=lambda c: tuple(v or "" for v in (
        c.treatment, c.task, c.prompt_variant, c.agent, c.task_version, c.check_version, c.treatment_version)))


def mean_usage(trials: list[TrialSummary], attribute: str) -> float | None:
    """Mean of a usage field over the ``trials`` that report it."""
    values = [getattr(t, attribute) for t in trials if getattr(t, attribute) is not None]
    return mean(values) if values else None


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
    config = _read_json(run_dir / "job/config.json") or {}
    environment_type = (config.get("environment") or {}).get("type", "")
    return RunSummary(
        path=run_dir,
        date=_parse_stamp(run_dir.name),
        task=task,
        prompt_variant=prompt_variant,
        treatment=treatment,
        agent=agent,
        environment=ENVIRONMENTS.get(environment_type, environment_type),
        trials=[summarise_trial(path, record) for path, record in zip(trial_dirs, records)],
        fingerprints=fingerprints,
    )


def summarise_trial(trial_dir: Path, record: dict | None) -> TrialSummary:
    files = {label: trial_dir / rel for label, rel in KEY_FILES.items() if (trial_dir / rel).exists()}
    if record is None:
        return TrialSummary(path=trial_dir, status="unrecorded", files=files)

    checks = record.get("checks") or []
    preferred = [check["passed"] for check in checks if not check["required"]]
    usage = record.get("usage") or {}
    token_counts = [usage[key] for key in ("n_input_tokens", "n_output_tokens") if usage.get(key) is not None]
    result = _read_json(trial_dir / "result.json") or {}
    trajectory = _read_json(trial_dir / "agent/trajectory.json")
    return TrialSummary(
        path=trial_dir,
        status=record["status"],
        record=record,
        preferred_passed=all(preferred) if preferred else None,
        failed_required=[c["name"] for c in checks if c["required"] and not c["passed"]],
        failed_preferred=[c["name"] for c in checks if not c["required"] and not c["passed"]],
        cost_usd=usage.get("cost_usd"),
        tokens=sum(token_counts) if token_counts else None,
        # A turn is one agent message in Harbor's trajectory, with or without tool calls.
        turns=sum(step.get("source") == "agent" for step in trajectory["steps"]) if trajectory else None,
        duration_s=_duration_s(result.get("agent_execution")),
        files=files,
    )


def collect_tasks(tasks_dir: Path) -> list[TaskDefinition]:
    """Read every Task under ``tasks_dir`` (``tasks/<stage>/<scenario>/``),
    ordered by path. Task pages are read from the sibling ``docs/tasks/``."""
    repo = tasks_dir.parent
    return [read_task(task_toml.parent, repo) for task_toml in sorted(tasks_dir.glob("*/*/task.toml"))]


def read_task(task_dir: Path, repo: Path) -> TaskDefinition:
    path = task_dir.relative_to(repo).as_posix()
    page = repo / "docs" / (path + ".md")
    config = tomllib.loads((task_dir / "task.toml").read_text())
    metadata = config.get("metadata") or {}
    if "motivation" in metadata:
        motivation, summary = (" ".join(metadata.get(key, "").split()) for key in ("motivation", "summary"))
    else:
        motivation, summary = _read_task_page(page) if page.is_file() else ("", "")
    prompts = {"default": (task_dir / "instruction.md").read_text()}
    for prompt in sorted((task_dir / "prompts").glob("*.md")):
        prompts[prompt.stem] = prompt.read_text()
    checks, check_error, expected = _read_checks(task_dir / "check.py")
    return TaskDefinition(
        path=path,
        directory=task_dir,
        page=page if page.is_file() else None,
        motivation=motivation,
        summary=summary,
        prompts=prompts,
        checks=checks,
        check_error=check_error,
        config=config,
        expected=expected,
    )


def load_agents(agents_file: Path) -> dict[str, dict]:
    """Named Agents from ``agents.toml``, in file order; empty when the file is missing."""
    return tomllib.loads(agents_file.read_text()) if agents_file.is_file() else {}


def _read_checks(check_file: Path) -> tuple[list[CheckDefinition], str | None, dict]:
    # A per-Task module name keeps Tasks' check modules apart; none is added to
    # sys.modules, so `weval check` and tests import their own copies.
    name = "weval_report_check_" + "_".join(check_file.parent.parts[-2:]).replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, check_file)

    def definitions(functions: list, required: bool, prompt_variant: str | None = None) -> list[CheckDefinition]:
        return [
            CheckDefinition(
                id=function.__name__.replace("_", "-"),
                required=required,
                description=" ".join((inspect.getdoc(function) or "").split()),
                prompt_variant=prompt_variant,
            )
            for function in functions
        ]

    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checks = definitions(module.REQUIRED, True) + definitions(module.PREFERRED, False)
        for attribute, required in (("PROMPT_VARIANT_REQUIRED", True), ("PROMPT_VARIANT_PREFERRED", False)):
            for prompt_variant, functions in getattr(module, attribute, {}).items():
                checks += definitions(functions, required, prompt_variant)
    except Exception as error:  # noqa: BLE001  A broken Task must not break the report.
        return [], "".join(traceback.format_exception_only(error)).strip(), {}
    return checks, None, getattr(module, "EXPECTED", {})


def _read_task_page(page: Path) -> tuple[str, str]:
    """Return the page's front-matter ``motivation`` and its first paragraph
    after the title, each joined into one line."""
    text = page.read_text()
    front_matter, body = "", text
    if text.startswith("---\n"):
        front_matter, _, body = text[4:].partition("\n---\n")

    # The front matter holds one folded scalar; a YAML parser is not a runtime dependency.
    motivation_lines, in_motivation = [], False
    for line in front_matter.splitlines():
        if line.startswith("motivation:"):
            in_motivation = True
            value = line.removeprefix("motivation:").strip()
            if value not in (">", "|", ">-", "|-"):
                motivation_lines.append(value)
        elif in_motivation and line.startswith((" ", "\t")):
            motivation_lines.append(line.strip())
        else:
            in_motivation = False

    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    summary = next((p for p in paragraphs if not p.startswith("#")), "")
    return " ".join(motivation_lines), " ".join(summary.split())


def _duration_s(span: dict | None) -> float | None:
    if not span or not span.get("started_at") or not span.get("finished_at"):
        return None
    started, finished = (datetime.fromisoformat(span[key]) for key in ("started_at", "finished_at"))
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
