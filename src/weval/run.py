"""Run a Task with an Agent through Harbor on Modal, then record each Trial.

Output layout, one directory per invocation::

    experiment-outputs/<timestamp>-<task>-<agent>/
        task/                 Harbor task package built from tasks/<task>/
        job/<trial>/          Harbor's Trial directory, kept as Harbor wrote it
        job/<trial>/weval.json  Agent, status, missing logs, check results
"""

import asyncio
import importlib.util
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

from weval import verify
from weval.harnesses import oracle, pi

ROOT = Path(__file__).resolve().parents[2]
HARNESSES: dict[str, ModuleType] = {"oracle": oracle, "pi": pi}
# Appended to every packaged prompt: facts about the Trial environment that no
# single Task owns.
SHARED_INSTRUCTIONS = Path(__file__).with_name("shared-instructions.md")
# Every Trial must have these, whatever the harness.
COMMON_LOGS = ("verifier/snapshot.json", "verifier/checks.json", "artifacts/submission")
SECRET_VARS = ("OPENROUTER_API_KEY", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET")

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


def package_task(task_dir: Path, destination: Path) -> None:
    """Build a Harbor task package: the Task directory plus ``tests/``, which
    holds the shared verifier with the Task's snapshot and check. The packaged
    ``instruction.md`` ends with the shared instructions."""
    shutil.copytree(
        task_dir,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "snapshot.py", "check.py"),
    )
    instruction = destination / "instruction.md"
    instruction.write_text(f"{instruction.read_text()}\n{SHARED_INSTRUCTIONS.read_text()}")
    tests = destination / "tests"
    tests.mkdir()
    shutil.copy(Path(verify.__file__), tests / "verify.py")
    shutil.copy(task_dir / "snapshot.py", tests)
    shutil.copy(task_dir / "check.py", tests)
    (tests / "test.sh").write_text(
        "#!/bin/sh\nexport PYTHONDONTWRITEBYTECODE=1\nexec python3 /tests/verify.py\n"
    )
    (tests / "test.sh").chmod(0o755)


def run(task_dir: Path, agent_name: str, attempts: int = 1) -> Path:
    """Run ``attempts`` Trials of one Task by one Agent; return the run directory.

    Harbor failures inside a Trial are recorded as Non-results in ``weval.json``,
    not raised. Retained files are scrubbed of credential values afterwards,
    even when Harbor itself raised.
    """
    task_dir = task_dir.resolve()
    agents = tomllib.loads((ROOT / "agents.toml").read_text())
    agent = {"name": agent_name, **agents[agent_name]}
    harness = HARNESSES[agent["harness"]]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "experiment-outputs" / f"{stamp}-{task_dir.name}-{agent_name}"
    package_task(task_dir, run_dir / "task")
    config = JobConfig(
        job_name="job",
        jobs_dir=run_dir,
        tasks=[TaskConfig(path=run_dir / "task")],
        agents=[harness.agent_config(agent)],
        n_attempts=attempts,
        n_concurrent_trials=attempts,
        environment=MODAL,
    )
    try:
        asyncio.run(_run_job(config))
    finally:
        for result_file in sorted((run_dir / "job").glob("*/result.json")):
            record = finalize(result_file.parent, task_dir, agent)
            print(f"{result_file.parent}: {record['status']}")
        redact(run_dir)
    return run_dir


async def _run_job(config: JobConfig) -> None:
    job = await Job.create(config)
    await job.run()


def finalize(trial_dir: Path, task_dir: Path, agent: dict) -> dict:
    """Write and return ``weval.json`` for one Harbor Trial directory.

    Status is ``non-result`` when Harbor raised or the verifier produced no
    reward, ``incomplete`` when an expected log is missing, otherwise
    ``passed`` or ``failed`` by reward.
    """
    harness = HARNESSES[agent["harness"]]
    result = json.loads((trial_dir / "result.json").read_text())
    expected = COMMON_LOGS + harness.EXPECTED_LOGS
    missing = [pattern for pattern in expected if not any(trial_dir.glob(pattern))]
    checks_file = trial_dir / "verifier/checks.json"
    rewards = (result.get("verifier_result") or {}).get("rewards") or {}
    if result.get("exception_info") or "reward" not in rewards:
        status = "non-result"
    elif missing:
        status = "incomplete"
    else:
        status = "passed" if rewards["reward"] == 1 else "failed"
    record = {
        "status": status,
        "task": str(task_dir),
        "agent": harness.agent_record(agent),
        "agent_info": result.get("agent_info"),
        "reward": rewards.get("reward"),
        "exception": (result.get("exception_info") or {}).get("exception_type"),
        "missing_logs": missing,
        "checks": json.loads(checks_file.read_text()) if checks_file.exists() else None,
    }
    (trial_dir / "weval.json").write_text(json.dumps(record, indent=1))
    return record


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

    ``task_dir`` defaults to the Task recorded in the Trial's ``weval.json``.
    Retained files are not modified.
    """
    if task_dir is None:
        task_dir = Path(json.loads((trial_dir / "weval.json").read_text())["task"])
    spec = importlib.util.spec_from_file_location("check", task_dir / "check.py")
    assert spec and spec.loader
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    snapshot = json.loads((trial_dir / "verifier/snapshot.json").read_text())
    return verify.score(check, snapshot)
