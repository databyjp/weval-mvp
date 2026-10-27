"""Run a Task with an Agent through Harbor on Modal, then record each Trial.

Output layout, one directory per invocation::

    experiment-outputs/<timestamp>__<stage>__<scenario>[@<prompt-variant>]__<agent>[+<treatment>]/
        task/                 Harbor task package built from tasks/<stage>/<scenario>/
        treatment/            copy of treatments/<treatment>/, when given
        job/<trial>/          Harbor's Trial directory, kept as Harbor wrote it
        job/<trial>/weval.json  Agent, status, missing logs, check results, fingerprints
"""

import asyncio
import hashlib
import importlib.util
import json
import os
import re
import shutil
import tomllib
from datetime import datetime
from pathlib import Path
from types import ModuleType

from harbor.job import Job
from harbor.models.environment_type import EnvironmentType
from harbor.models.job.config import JobConfig
from harbor.models.trial.config import EnvironmentConfig, TaskConfig

from weval import verify
from weval.harnesses import claude_code, oracle, pi

ROOT = Path(__file__).resolve().parents[2]
TREATMENTS = ROOT / "treatments"
HARNESSES: dict[str, ModuleType] = {"oracle": oracle, "pi": pi, "claude-code": claude_code}
# Appended to every packaged prompt: facts about the Trial environment that no
# single Task owns.
SHARED_INSTRUCTIONS = Path(__file__).with_name("shared-instructions.md")
# Applied to every Trial environment: the workspace contract no single Task owns.
SHARED_COMPOSE = Path(__file__).with_name("shared-compose.yaml")
# Applied after it unless the Task opts out (see compose_overlays).
WEAVIATE_COMPOSE = Path(__file__).with_name("weaviate-compose.yaml")
# Every Trial must have these, whatever the harness.
COMMON_LOGS = ("verifier/snapshot.json", "verifier/checks.json", "artifacts/submission")
SECRET_VARS = ("OPENROUTER_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET")
# Harbor's per-Trial token and cost fields in result.json's agent_result.
USAGE_FIELDS = ("n_input_tokens", "n_cache_tokens", "n_output_tokens", "cost_usd")
# A URL's host must contain a dot, which excludes Compose service names such as
# weaviate:8080 and localhost; loopback addresses are excluded separately.
# Backslashes end a URL because arguments are matched in their JSON encoding.
URL = re.compile(r"https?://(?!127\.0\.0\.1|0\.0\.0\.0)[^\s/'\"`:\\]+\.[^\s/'\"`:\\]+[^\s'\"`<>)\]}\\]*")

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


def package_task(task_dir: Path, destination: Path, prompt_variant: str = "default") -> None:
    """Build a Harbor task package: the Task directory plus ``tests/``, which
    holds the shared verifier with the Task's snapshot and check. The packaged
    ``instruction.md`` is the prompt variant followed by the shared
    instructions: the Task's ``instruction.md`` for ``default``, otherwise
    ``prompts/<prompt-variant>.md``, which must exist.
    ``tests/prompt_variant`` holds the prompt variant name for the verifier."""
    prompt = task_dir / ("instruction.md" if prompt_variant == "default" else f"prompts/{prompt_variant}.md")
    if not prompt.exists():
        raise FileNotFoundError(f"no prompt for prompt variant {prompt_variant!r}: {prompt}")
    shutil.copytree(
        task_dir,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "snapshot.py", "check.py", "prompts"),
    )
    instruction = destination / "instruction.md"
    instruction.write_text(f"{prompt.read_text()}\n{SHARED_INSTRUCTIONS.read_text()}")
    tests = destination / "tests"
    tests.mkdir()
    (tests / "prompt_variant").write_text(prompt_variant)
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
    prompt_variant: str = "default",
    treatment: str | None = None,
) -> Path:
    """Run ``attempts`` Trials of one Task's prompt variant by one Agent on
    Modal, or on the local Docker daemon when ``local``; return the run
    directory. With ``treatment``, the Agent gets that Treatment's skills
    (``treatment_skills``).

    Harbor failures inside a Trial are recorded as Non-results in ``weval.json``,
    not raised. Retained files are scrubbed of credential values afterwards,
    even when Harbor itself raised.
    """
    task_dir = task_dir.resolve()
    # weval.json records the Task path relative to the repo, so a Task outside
    # it fails here rather than after the Trials have run.
    task_path = task_dir.relative_to(ROOT)
    agents = tomllib.loads((ROOT / "agents.toml").read_text())
    agent = {"name": agent_name, **agents[agent_name]}
    harness = HARNESSES[agent["harness"]]
    skills = treatment_skills(treatment) if treatment else None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Task and Agent names contain dashes; Harbor's "__" keeps the parts separable.
    scenario = task_dir.name if prompt_variant == "default" else f"{task_dir.name}@{prompt_variant}"
    agent_part = agent_name if treatment is None else f"{agent_name}+{treatment}"
    run_name = f"{stamp}__{task_dir.parent.name}__{scenario}__{agent_part}"
    run_dir = ROOT / "experiment-outputs" / run_name
    environment = (LOCAL if local else MODAL).model_copy(
        update={"extra_docker_compose": compose_overlays(task_dir)}
    )
    # Before the run directory exists, so a failed preparation leaves no empty run.
    if not local and hasattr(harness, "modal_environment"):
        environment = harness.modal_environment(agent, environment)
    package_task(task_dir, run_dir / "task", prompt_variant)
    agent_config = harness.agent_config(agent)
    if skills:
        # Harbor installs the retained copy, so the run keeps the skills its Trials had.
        shutil.copytree(skills.parent, run_dir / "treatment", ignore=shutil.ignore_patterns(".*"))
        agent_config.skills = [str(run_dir / "treatment/skills")]
    # Before the Trials run, so the fingerprints cover exactly what they were given.
    versions = fingerprints(run_dir, compose_overlays(task_dir))
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
        finalize_run(run_dir, task_path, agent, attempts, prompt_variant, treatment, versions)
        redact(run_dir)
    return run_dir


def treatment_skills(treatment: str) -> Path:
    """Return ``treatments/<treatment>/skills/``, whose subdirectories each
    hold one skill's ``SKILL.md``; Harbor installs them for the Agent's
    harness. Raises ``FileNotFoundError`` when the directory is missing, and
    Harbor fails each Trial when a subdirectory has no ``SKILL.md``."""
    skills = TREATMENTS / treatment / "skills"
    if not skills.is_dir():
        raise FileNotFoundError(f"no skills for Treatment {treatment!r}: {skills}")
    return skills


def fingerprints(run_dir: Path, overlays: list[Path]) -> dict[str, str | None]:
    """Content hashes that version what a run's Trials were given, for
    ``weval.json``'s ``fingerprints``.

    - ``task``: the packaged Task in ``run_dir/task`` (the prompt with the
      shared instructions, the environment, ``snapshot.py``, and the
      verifier) without ``check.py``, plus the Compose ``overlays``. A
      change here needs new Trials.
    - ``check``: the packaged ``check.py``. A change here needs only a
      re-score (``weval check``).
    - ``treatment``: the run's ``treatment/`` copy, or ``None`` for a baseline.

    Each is 12 hex digits of a SHA-256 over file paths and contents, so it is
    independent of timestamps and directory order.
    """
    package = run_dir / "task"
    check = package / "tests/check.py"
    task_files = {str(path.relative_to(package)): path for path in _tree(package) if path != check}
    task_files |= {f"overlays/{path.name}": path for path in overlays}
    treatment = run_dir / "treatment"
    return {
        "task": _digest(task_files),
        "check": _digest({"check.py": check}),
        "treatment": _digest({str(path.relative_to(treatment)): path for path in _tree(treatment)})
        if treatment.exists() else None,
    }


def _tree(root: Path) -> list[Path]:
    # Bytecode and dotfiles (.gitkeep, .DS_Store) don't change what a Trial is given.
    return [
        path for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]


def _digest(files: dict[str, Path]) -> str:
    sha = hashlib.sha256()
    for name in sorted(files):
        sha.update(name.encode() + b"\0" + files[name].read_bytes() + b"\0")
    return sha.hexdigest()[:12]


def compose_overlays(task_dir: Path) -> list[Path]:
    """The Compose overlays weval adds to the Task's Trial environment, in
    the order Harbor applies them. The Weaviate settings are left out when
    ``task.toml`` sets ``[metadata] weaviate_workspace = false``, for a Task
    whose workspace must not suggest a data store."""
    metadata = tomllib.loads((task_dir / "task.toml").read_text()).get("metadata", {})
    return [SHARED_COMPOSE] + ([WEAVIATE_COMPOSE] if metadata.get("weaviate_workspace", True) else [])


async def _run_job(config: JobConfig) -> None:
    job = await Job.create(config)
    await job.run()


def finalize_run(
    run_dir: Path,
    task_path: Path,
    agent: dict,
    attempts: int,
    prompt_variant: str = "default",
    treatment: str | None = None,
    versions: dict[str, str | None] | None = None,
) -> None:
    """Record every Trial directory under ``run_dir/job`` and print its status.
    ``versions`` is the run's ``fingerprints()``, recorded in every Trial.

    A Trial without ``result.json`` (Harbor stops the environment before
    writing it, so a stop failure or kill can leave none) gets a
    ``non-result`` stub naming the cause, so no Trial vanishes from the
    record. Warns when fewer Trial directories exist than ``attempts``.
    """
    trial_dirs = sorted(path for path in (run_dir / "job").glob("*") if path.is_dir())
    for trial_dir in trial_dirs:
        if (trial_dir / "result.json").exists():
            record = finalize(trial_dir, task_path, agent, prompt_variant, treatment, versions)
        else:
            record = {
                "status": "non-result",
                "task": str(task_path),
                "prompt_variant": prompt_variant,
                "treatment": treatment,
                "fingerprints": versions,
                "agent": HARNESSES[agent["harness"]].agent_record(agent),
                "reward": None,
                "exception": "result.json never written",
            }
            (trial_dir / "weval.json").write_text(json.dumps(record, indent=1))
        print(f"{trial_dir}: {record['status']}")
    if len(trial_dirs) < attempts:
        print(f"WARNING: {attempts} Trials requested, {len(trial_dirs)} found under {run_dir / 'job'}")


def derive_status(result: dict, missing: list[str]) -> str:
    """Classify one Trial by whose outcome it records (statuses: docs/reference.md).

    The snapshot plays no part: a snapshot error at any ``error_stage`` was
    graded, so it scores ``failed``. A ``snapshot``-stage error usually means
    the agent left its stack broken; a scorer bug is told apart when the
    failure is classified.
    """
    rewards = (result.get("verifier_result") or {}).get("rewards") or {}
    if "reward" not in rewards:
        return "non-result"
    if result.get("exception_info"):
        return "timed-out"
    if missing:
        return "incomplete"
    return "passed" if rewards["reward"] == 1 else "failed"


def finalize(
    trial_dir: Path,
    task_path: Path,
    agent: dict,
    prompt_variant: str = "default",
    treatment: str | None = None,
    versions: dict[str, str | None] | None = None,
) -> dict:
    """Write and return ``weval.json`` for one Harbor Trial directory.

    ``task_path`` is recorded as given; ``run()`` passes it relative to the
    repository root. ``treatment`` is ``None`` for a baseline Trial.
    ``versions`` is the run's ``fingerprints()``; ``None`` records the Trial
    as unversioned.

    Status comes from ``derive_status`` over Harbor's ``result.json`` and the
    missing-log list.
    """
    harness = HARNESSES[agent["harness"]]
    result = json.loads((trial_dir / "result.json").read_text())
    expected = COMMON_LOGS + harness.EXPECTED_LOGS
    missing = [pattern for pattern in expected if not any(trial_dir.glob(pattern))]
    checks_file = trial_dir / "verifier/checks.json"
    snapshot_file = trial_dir / "verifier/snapshot.json"
    snapshot = json.loads(snapshot_file.read_text()) if snapshot_file.exists() else None
    rewards = (result.get("verifier_result") or {}).get("rewards") or {}
    record = {
        "status": derive_status(result, missing),
        "task": str(task_path),
        "prompt_variant": prompt_variant,
        "treatment": treatment,
        "fingerprints": versions,
        "agent": harness.agent_record(agent),
        "agent_info": result.get("agent_info"),
        "reward": rewards.get("reward"),
        "exception": (result.get("exception_info") or {}).get("exception_type"),
        "error_stage": (snapshot or {}).get("error_stage"),
        "missing_logs": missing,
        "checks": json.loads(checks_file.read_text()) if checks_file.exists() else None,
        # A harness that counts requests Harbor misses replaces Harbor's figures.
        "usage": usage(trial_dir, result) | (
            harness.token_usage(trial_dir) if hasattr(harness, "token_usage") else {}
        ),
    }
    (trial_dir / "weval.json").write_text(json.dumps(record, indent=1))
    return record


def usage(trial_dir: Path, result: dict) -> dict:
    """Return the Agent's token use and web lookups for ``weval.json``.

    Tokens and cost come from Harbor's ``result.json`` and are ``None`` when
    the harness reports none, as for the Oracle. ``finalize()`` replaces them
    with a harness module's ``token_usage(trial_dir)`` when it defines one. ``tool_calls`` counts calls
    by tool name. ``urls`` lists, in first-use order, every external URL in
    any tool call's arguments, including ``curl`` commands; a page read from
    search results without its own fetch is not listed. ``search_queries``
    lists every ``query`` or ``queries`` argument. All three are empty
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
            urls.update(dict.fromkeys(URL.findall(json.dumps(arguments))))
            query = arguments.get("queries") or arguments.get("query") or []
            queries.extend([query] if isinstance(query, str) else query)
    return {**record, "tool_calls": tool_calls, "urls": list(urls), "search_queries": queries}


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


def rescore(trial_dir: Path, task_dir: Path | None = None) -> list[dict]:
    """Re-score a retained ``snapshot.json`` with a Task's current ``check.py``.

    ``task_dir`` defaults to the Task recorded in the Trial's ``weval.json``,
    resolved against the repository root. Retained files are not modified.
    """
    if task_dir is None:
        task_dir = ROOT / json.loads((trial_dir / "weval.json").read_text())["task"]
    spec = importlib.util.spec_from_file_location("check", task_dir / "check.py")
    assert spec and spec.loader
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    snapshot = json.loads((trial_dir / "verifier/snapshot.json").read_text())
    return verify.score(check, snapshot)
