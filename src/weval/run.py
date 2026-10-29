"""Run a Task with an Agent through Harbor on Modal, then record each Trial.

Output layout, one directory per invocation::

    experiment-outputs/<timestamp>__<stage>__<scenario>__<agent>[+<treatment>]/
        task/                 Harbor task package built from tasks/<stage>/<scenario>/
        treatment/            copy of treatments/<treatment>/, when given
        labels/<trial>.json   saved Jev labels for the Trial's failed checks (weval.labels)
        job/<trial>/          Harbor's Trial directory, kept as Harbor wrote it
        job/<trial>/weval.json  Agent, status, missing logs, check results, fingerprints
    experiment-outputs/_analysis/<comparison>.json  saved analysis of each Treatment comparison (weval.analysis)
"""

import asyncio
import hashlib
import json
import os
import shutil
import tomllib
from datetime import datetime
from pathlib import Path
from types import ModuleType

from harbor.job import Job
from harbor.models.environment_type import EnvironmentType
from harbor.models.job.config import JobConfig
from harbor.models.trial.config import EnvironmentConfig, TaskConfig

from weval import diagnostics, labels, verify
from weval.harnesses import claude_code, oracle, pi

ROOT = Path(__file__).resolve().parents[2]
TREATMENTS = ROOT / "treatments"
HARNESSES: dict[str, ModuleType] = {
    "oracle": oracle,
    "pi": pi,
    "claude-code": claude_code,
}
# Appended to every packaged prompt of a Task that uses Docker: facts about the
# Trial environment that no single Task owns.
SHARED_INSTRUCTIONS = Path(__file__).with_name("shared-instructions.md")
# Applied to every Trial environment of a Task that uses Docker: the workspace
# contract no single Task owns, including the Docker socket.
SHARED_COMPOSE = Path(__file__).with_name("shared-compose.yaml")
# Applied after it unless the Task opts out (see compose_overlays).
WEAVIATE_COMPOSE = Path(__file__).with_name("weaviate-compose.yaml")
# Every Trial must have these, whatever the harness.
COMMON_LOGS = ("verifier/snapshot.json", "verifier/checks.json", "artifacts/submission")
SECRET_VARS = (
    "OPENROUTER_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "MODAL_TOKEN_ID",
    "MODAL_TOKEN_SECRET",
    "TYPESAFEAI_API_KEY",
)
# Harbor's per-Trial token and cost fields in result.json's agent_result.
USAGE_FIELDS = ("n_input_tokens", "n_cache_tokens", "n_output_tokens", "cost_usd")
# VM with Docker-in-Docker so Tasks can run their own Compose stacks.
MODAL = EnvironmentConfig(
    type=EnvironmentType.MODAL,
    delete=True,
    override_cpus=4,
    override_memory_mb=8192,
    kwargs={
        "modal_vm_runtime": True,
        "region": "eu",
        "sandbox_timeout_secs": 3600,
        "sandbox_idle_timeout_secs": 1800,
    },
)
# The local Docker daemon, for Tasks that run without Docker-in-Docker.
LOCAL = EnvironmentConfig(
    type=EnvironmentType.DOCKER,
    delete=True,
)


def package_task(task_dir: Path, destination: Path, prompt: Path | None = None) -> None:
    """Build a Harbor task package: the Task directory plus ``tests/``, which
    holds the shared verifier with the Task's snapshot and check. The packaged
    ``instruction.md`` is ``prompt``, a Treatment's replacement for the Task's
    own ``instruction.md`` (the default), followed by the shared instructions
    unless the Task has no Docker (``uses_docker``)."""
    prompt = prompt or task_dir / "instruction.md"
    shutil.copytree(
        task_dir,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "snapshot.py", "check.py"),
    )
    instruction = destination / "instruction.md"
    notes = f"\n{SHARED_INSTRUCTIONS.read_text()}" if uses_docker(task_dir) else ""
    instruction.write_text(prompt.read_text() + notes)
    tests = destination / "tests"
    tests.mkdir()
    shutil.copy(Path(verify.__file__), tests / "verify.py")
    shutil.copy(task_dir / "snapshot.py", tests)
    shutil.copy(task_dir / "check.py", tests)
    (tests / "test.sh").write_text(
        "#!/bin/sh\nexport PYTHONDONTWRITEBYTECODE=1\nexec python3 /tests/verify.py\n"
    )
    (tests / "test.sh").chmod(0o755)


def run(
    task_dir: Path,
    agent_name: str,
    attempts: int = 1,
    local: bool = False,
    treatment: str | None = None,
    draft: bool = False,
    unsafe_local: bool = False,
) -> Path:
    """Run ``attempts`` Trials of one Task by one Agent on Modal, or on the
    local Docker daemon when ``local``; return the run directory. With
    ``treatment``, the Agent gets that Treatment's skills, its prompt for the
    Task, or both (``treatment_files``). A draft Task (``task.toml`` sets ``[metadata]
    draft = true``) raises ``ValueError`` unless ``draft``, before anything
    runs or is written. So does a local run of a non-Oracle Agent on a Task
    that uses Docker, unless ``unsafe_local``: the agent's container would
    hold the host's Docker socket, which is root on the host.

    Harbor failures inside a Trial are recorded as Non-results in ``weval.json``,
    not raised. Retained files are scrubbed of credential values afterwards,
    even when Harbor itself raised.
    """
    task_dir = task_dir.resolve()
    if task_metadata(task_dir).get("draft") and not draft:
        raise ValueError(
            f"{task_dir.name} is a draft Task ([metadata] draft = true in its "
            "task.toml); pass --draft to run it anyway"
        )
    agents = tomllib.loads((ROOT / "agents.toml").read_text())
    agent = {"name": agent_name, **agents[agent_name]}
    harness = HARNESSES[agent["harness"]]
    if local and harness is not oracle and uses_docker(task_dir) and not unsafe_local:
        raise ValueError(
            f"{task_dir.name} uses Docker, so a local Trial would give "
            f"{agent_name}'s container the host's Docker socket, which is root on "
            "the host and reaches the credentials in .env; run it on Modal, or "
            "pass --unsafe-local to accept that"
        )
    # weval.json records the Task path relative to the repo, so a Task outside
    # it fails here rather than after the Trials have run.
    task_path = task_dir.relative_to(ROOT)
    skills, prompt = (
        treatment_files(treatment, task_path) if treatment else (None, None)
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Task and Agent names contain dashes; Harbor's "__" keeps the parts separable.
    agent_part = agent_name if treatment is None else f"{agent_name}+{treatment}"
    run_name = f"{stamp}__{task_dir.parent.name}__{task_dir.name}__{agent_part}"
    run_dir = ROOT / "experiment-outputs" / run_name
    environment = (LOCAL if local else MODAL).model_copy(
        update={"extra_docker_compose": compose_overlays(task_dir)}
    )
    # Before the run directory exists, so a failed preparation leaves no empty run.
    if not local and hasattr(harness, "modal_environment"):
        environment = harness.modal_environment(agent, environment)
    package_task(task_dir, run_dir / "task", prompt)
    agent_config = harness.agent_config(agent)
    if treatment:
        # Harbor installs the retained copy, so the run keeps the skills its Trials had.
        shutil.copytree(
            TREATMENTS / treatment,
            run_dir / "treatment",
            ignore=shutil.ignore_patterns(".*"),
        )
    if skills:
        agent_config.skills = [str(run_dir / "treatment/skills")]
    # Before the Trials run, so the fingerprints cover exactly what they were given.
    versions = fingerprints(task_dir, skills, prompt)
    config = JobConfig(
        job_name="job",
        jobs_dir=run_dir,
        tasks=[TaskConfig(path=run_dir / "task")],
        agents=[agent_config],
        n_attempts=attempts,
        n_concurrent_trials=attempts,
        environment=environment,
    )
    try:
        asyncio.run(_run_job(config))
    finally:
        # The scrub must not depend on recording or labelling, which can raise.
        try:
            finalize_run(run_dir, task_path, agent, attempts, treatment, versions)
        finally:
            redact(run_dir)
        # Analysis is not run here: a comparison spans every Agent's runs, so
        # it is analysed once, by `weval analyse`, after the batch.
        label_run(run_dir)
    return run_dir


def treatment_files(treatment: str, task_path: Path) -> tuple[Path | None, Path | None]:
    """Return what ``treatments/<treatment>/`` gives the Agent on the Task at
    ``task_path`` (``tasks/<stage>/<scenario>``): its ``skills/``, whose
    subdirectories each hold one skill's ``SKILL.md`` for Harbor to install,
    and its ``prompts/<stage>/<scenario>.md``, which replaces the Task's
    prompt. Either is ``None`` when the Treatment has none.

    Raises ``FileNotFoundError`` when the Treatment has neither, or has
    prompts but none for this Task. Harbor fails each Trial when a skill
    subdirectory has no ``SKILL.md``."""
    directory = TREATMENTS / treatment
    skills = directory / "skills"
    prompts = directory / "prompts"
    prompt = prompts / f"{task_path.relative_to('tasks')}.md"
    if prompts.is_dir() and not prompt.is_file():
        raise FileNotFoundError(
            f"Treatment {treatment!r} has no prompt for this Task: {prompt}"
        )
    if not skills.is_dir() and not prompts.is_dir():
        raise FileNotFoundError(
            f"Treatment {treatment!r} has no skills/ or prompts/: {directory}"
        )
    return (
        skills if skills.is_dir() else None,
        prompt if prompts.is_dir() else None,
    )


def fingerprints(
    task_dir: Path, skills: Path | None = None, prompt: Path | None = None
) -> dict[str, str | None]:
    """Content hashes that version what a run's Trials were given, for
    ``weval.json``'s ``fingerprints``.

    - ``task``: the Task directory without ``check.py``, plus what packaging
      and the environment add: the shared instructions, ``verify.py``, and
      the Compose overlays. A change here needs new Trials.
    - ``check``: the Task's ``check.py``. A change here needs only a
      re-score (``weval check``).
    - ``treatment``: what the Treatment gives the Agent on this Task: its
      ``skills`` and its replacement ``prompt``, or ``None`` for a baseline.
      Its ``README.md`` and its prompts for other Tasks are not covered.

    Each is 12 hex digits of a SHA-256 over file paths and contents, so it is
    independent of timestamps and directory order.
    """
    check = task_dir / "check.py"
    task_files = {
        str(path.relative_to(task_dir)): path
        for path in _tree(task_dir)
        if path != check
    }
    added = [
        *([SHARED_INSTRUCTIONS] if uses_docker(task_dir) else []),
        Path(verify.__file__),
        *compose_overlays(task_dir),
    ]
    task_files |= {f"weval/{path.name}": path for path in added}
    return {
        "task": _digest(task_files),
        "check": check_fingerprint(check),
        "treatment": _treatment_digest(skills, prompt) if skills or prompt else None,
    }


def _treatment_digest(skills: Path | None, prompt: Path | None) -> str:
    # Skill paths are relative to skills/, so a Treatment without a prompt
    # keeps the fingerprint it had before Treatments could carry prompts.
    files = (
        {str(path.relative_to(skills)): path for path in _tree(skills)}
        if skills
        else {}
    )
    if prompt:
        files["prompt.md"] = prompt
    return _digest(files)


def check_fingerprint(check_file: Path) -> str:
    """The ``check`` fingerprint of a ``check.py``."""
    return _digest({"check.py": check_file})


def _tree(root: Path) -> list[Path]:
    # Bytecode and dotfiles (.gitkeep, .DS_Store) don't change what a Trial is given.
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]


def _digest(files: dict[str, Path]) -> str:
    sha = hashlib.sha256()
    for name in sorted(files):
        sha.update(name.encode() + b"\0" + files[name].read_bytes() + b"\0")
    return sha.hexdigest()[:12]


def compose_overlays(task_dir: Path) -> list[Path]:
    """The Compose overlays weval adds to the Task's Trial environment, in
    the order Harbor applies them. The shared overlay, which mounts the
    Docker socket, is left out for a Task without Docker (``uses_docker``).
    The Weaviate settings are left out when ``task.toml`` sets ``[metadata]
    weaviate_workspace = false``, for a Task whose workspace must not suggest
    a data store."""
    return ([SHARED_COMPOSE] if uses_docker(task_dir) else []) + (
        [WEAVIATE_COMPOSE]
        if task_metadata(task_dir).get("weaviate_workspace", True)
        else []
    )


def uses_docker(task_dir: Path) -> bool:
    """Whether the Task's agent gets the host's Docker daemon and the
    environment notes about it. ``task.toml`` sets ``[metadata] docker =
    false`` for a Task that runs no stack, so that any Agent can run it
    locally (``run``'s ``unsafe_local``)."""
    return task_metadata(task_dir).get("docker", True)


def task_metadata(task_dir: Path) -> dict:
    """The ``[metadata]`` table of the Task's ``task.toml``, where weval reads
    its own Task settings; Harbor's schema leaves the table free-form."""
    return tomllib.loads((task_dir / "task.toml").read_text()).get("metadata", {})


async def _run_job(config: JobConfig) -> None:
    job = await Job.create(config)
    await job.run()


def finalize_run(
    run_dir: Path,
    task_path: Path,
    agent: dict,
    attempts: int,
    treatment: str | None = None,
    versions: dict[str, str | None] | None = None,
) -> None:
    """Record every Trial directory under ``run_dir/job`` and print its status.
    ``versions`` is the run's ``fingerprints()``, recorded in every Trial.

    A Trial without ``result.json`` (Harbor stops the environment before
    writing it, so a stop failure or kill can leave none), or whose files
    ``finalize`` cannot read, gets a ``non-result`` stub naming the cause, so
    no Trial vanishes from the record and the others are still recorded.
    Warns when fewer Trial directories exist than ``attempts``.
    """
    trial_dirs = sorted(path for path in (run_dir / "job").glob("*") if path.is_dir())
    for trial_dir in trial_dirs:
        record = None
        exception = "result.json never written"
        if (trial_dir / "result.json").exists():
            try:
                record = finalize(trial_dir, task_path, agent, treatment, versions)
            except Exception as error:  # noqa: BLE001  Record the other Trials.
                exception = f"recording failed: {error!r}"
        if record is None:
            record = {
                "status": "non-result",
                **_trial_identity(task_path, agent, treatment, versions),
                "reward": None,
                "exception": exception,
            }
            (trial_dir / "weval.json").write_text(json.dumps(record, indent=1))
        print(f"{trial_dir}: {record['status']}")
    if len(trial_dirs) < attempts:
        print(
            f"WARNING: {attempts} Trials requested, {len(trial_dirs)} found under {run_dir / 'job'}"
        )


def label_run(run_dir: Path) -> None:
    """Label each recorded Trial's failed checks (``labels.label``) and print
    any note. Labelling explains results, so a failure here is printed, not
    raised: the run's record is already complete."""
    for record_file in sorted((run_dir / "job").glob("*/weval.json")):
        checks = json.loads(record_file.read_text()).get("checks") or []
        try:
            note = labels.label(record_file.parent, checks)["note"]
        except Exception as error:  # noqa: BLE001  Labels must not break a finished run.
            note = f"labelling failed: {error!r}"
        if note:
            print(f"{record_file.parent}: {note}")


def analyse_run(run_dir: Path) -> None:
    """Refresh the analysis (``analysis.analyse``) of each Treatment
    comparison among the retained runs beside ``run_dir`` that includes it,
    and print each result. Like ``label_run``, a failure is printed, not
    raised."""
    # Imported here: analysis and its SDK are not needed to run Trials, and
    # importing rescore at the top would be circular (it imports weval.run).
    from weval import analysis
    from weval.collect import collect_runs, compare_treatments
    from weval.rescore import load_check

    for comparison in compare_treatments(collect_runs(run_dir.parent)):
        if run_dir.resolve() not in {
            run.path.resolve() for run in comparison.baseline + comparison.treated
        }:
            continue
        name = f"{comparison.treatment} on {comparison.task} across {len(comparison.agents)} Agents"
        try:
            result = analysis.analyse(
                comparison,
                getattr(load_check(ROOT / comparison.task), "EXPECTED", {}),
                run_dir.parent,
            )
        except Exception as error:  # noqa: BLE001  Analysis must not break a finished run.
            print(f"{name}: analysis failed: {error!r}")
            continue
        if result["analysis"]:
            print(f"{name}: {result['analysis']['result']}")
        if result["problems"]:
            print(f"{name}: analysis rejected: {'; '.join(result['problems'])}")
        for item in result["disagreements"]:
            print(
                f"{name}: {item['trial']} {item['check']}: analyst {item['analyst']}, rule {item['class']}"
            )
        if result["note"]:
            print(f"{name}: {result['note']}")


def derive_status(
    result: dict, missing: list[str], model_error: str | None = None
) -> str:
    """Classify one Trial by whose outcome it records (statuses: docs/reference.md).

    ``model_error`` is the harness's ``model_error``: a session ended by a
    failed model request is a ``non-result`` whatever was graded, because
    the agent never chose to stop. The snapshot plays no part: a snapshot error at any ``error_stage`` was
    graded, so it scores ``failed``. A ``snapshot``-stage error usually means
    the agent left its stack broken; a scorer bug is told apart when the
    failure is classified.
    """
    rewards = (result.get("verifier_result") or {}).get("rewards") or {}
    if "reward" not in rewards or model_error:
        return "non-result"
    if result.get("exception_info"):
        return "timed-out"
    if missing:
        return "incomplete"
    return "passed" if rewards["reward"] == 1 else "failed"


def _trial_identity(
    task_path: Path,
    agent: dict,
    treatment: str | None,
    versions: dict[str, str | None] | None,
) -> dict:
    """The fields every ``weval.json`` carries whatever the outcome: which
    Task, Treatment, fingerprints, and Agent the Trial ran.
    One construction path, so ``finalize`` and ``finalize_run``'s non-result
    stub cannot drift apart."""
    return {
        "task": str(task_path),
        "treatment": treatment,
        "fingerprints": versions,
        "agent": HARNESSES[agent["harness"]].agent_record(agent),
    }


def finalize(
    trial_dir: Path,
    task_path: Path,
    agent: dict,
    treatment: str | None = None,
    versions: dict[str, str | None] | None = None,
) -> dict:
    """Write and return ``weval.json`` for one Harbor Trial directory.

    ``task_path`` is recorded as given; ``run()`` passes it relative to the
    repository root. ``treatment`` is ``None`` for a baseline Trial.
    ``versions`` is the run's ``fingerprints()``; ``None`` records the Trial
    as unversioned.

    Status comes from ``derive_status`` over Harbor's ``result.json``, the
    missing-log list, and the harness's ``model_error``, recorded as
    ``model_error``.
    """
    harness = HARNESSES[agent["harness"]]
    result = json.loads((trial_dir / "result.json").read_text())
    expected = COMMON_LOGS + harness.EXPECTED_LOGS
    missing = [pattern for pattern in expected if not any(trial_dir.glob(pattern))]
    checks_file = trial_dir / "verifier/checks.json"
    snapshot_file = trial_dir / "verifier/snapshot.json"
    snapshot = json.loads(snapshot_file.read_text()) if snapshot_file.exists() else None
    rewards = (result.get("verifier_result") or {}).get("rewards") or {}
    model_error = (
        harness.model_error(trial_dir) if hasattr(harness, "model_error") else None
    )
    record = {
        "status": derive_status(result, missing, model_error),
        **_trial_identity(task_path, agent, treatment, versions),
        "agent_info": result.get("agent_info"),
        "reward": rewards.get("reward"),
        "exception": (result.get("exception_info") or {}).get("exception_type"),
        "model_error": model_error,
        "error_stage": (snapshot or {}).get("error_stage"),
        "missing_logs": missing,
        "checks": json.loads(checks_file.read_text()) if checks_file.exists() else None,
        # A harness that counts requests Harbor misses replaces Harbor's figures.
        "usage": usage(trial_dir, result)
        | (harness.token_usage(trial_dir) if hasattr(harness, "token_usage") else {}),
    }
    (trial_dir / "weval.json").write_text(json.dumps(record, indent=1))
    return record


def usage(trial_dir: Path, result: dict) -> dict:
    """Return the Agent's token use and web lookups for ``weval.json``.

    Tokens and cost come from Harbor's ``result.json`` and are ``None`` when
    the harness reports none, as for the Oracle. ``finalize()`` replaces them
    with a harness module's ``token_usage(trial_dir)`` when it defines one. ``tool_calls`` counts calls
    by tool name. ``urls`` lists, in first-use order, every external URL in
    any tool call's arguments, including ``curl`` commands and URLs built
    from a shell variable assigned in the same command; a page read from
    search results without its own fetch is not listed. ``search_queries``
    lists every ``query`` or ``queries`` argument except ``ToolSearch``'s. All three are empty
    without Harbor's ``agent/trajectory.json``.
    """
    agent_result = result.get("agent_result") or {}
    record: dict = {field: agent_result.get(field) for field in USAGE_FIELDS}
    tool_calls: dict[str, int] = {}
    urls: dict[str, None] = {}
    queries: list[str] = []
    trajectory = trial_dir / "agent/trajectory.json"
    steps = json.loads(trajectory.read_text())["steps"] if trajectory.exists() else []
    for step in steps:
        for call in step.get("tool_calls") or []:
            name, arguments = call["function_name"], call.get("arguments") or {}
            tool_calls[name] = tool_calls.get(name, 0) + 1
            urls.update(dict.fromkeys(diagnostics.urls_in(json.dumps(arguments))))
            # Claude Code's ToolSearch query selects tools, not web pages.
            query = (
                []
                if name == "ToolSearch"
                else arguments.get("queries") or arguments.get("query") or []
            )
            queries.extend([query] if isinstance(query, str) else query)
    return {
        **record,
        "tool_calls": tool_calls,
        "urls": list(urls),
        "search_queries": queries,
    }


def redact(run_dir: Path) -> None:
    """Replace any credential value found in retained files with a placeholder."""
    secrets = {var: os.environ[var] for var in SECRET_VARS if os.environ.get(var)}
    for path in run_dir.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        found = [var for var, value in secrets.items() if value.encode() in data]
        for var in found:
            data = data.replace(secrets[var].encode(), f"<redacted:{var}>".encode())
        if found:
            path.write_bytes(data)
            print(f"WARNING: redacted {', '.join(found)} from {path}")
