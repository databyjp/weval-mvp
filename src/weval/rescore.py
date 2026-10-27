"""Re-score retained Trials offline with a Task's current ``check.py``.

Serves ``weval check``: ``rescore`` scores a retained ``snapshot.json``,
``diagnose`` explains the results from the retained logs, and
``check_versions`` compares the ``check.py`` scored with against the one the
Trial recorded. Everything reads retained files without modifying them;
``weval.json`` keeps the scores from the original run.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from weval import diagnostics, verify
from weval.run import ROOT, check_fingerprint


def rescore(trial_dir: Path, task_dir: Path | None = None) -> list[dict]:
    """Re-score a retained ``snapshot.json`` with a Task's current ``check.py``.

    ``task_dir`` defaults to the Task recorded in the Trial's ``weval.json``,
    resolved against the repository root. Retained files are not modified.
    """
    check = load_check(task_dir or _recorded_task(trial_dir))
    snapshot = json.loads((trial_dir / "verifier/snapshot.json").read_text())
    return verify.score(check, snapshot)


def diagnose(
    trial_dir: Path, results: list[dict], task_dir: Path | None = None
) -> dict:
    """``diagnostics.diagnose`` for a retained Trial and its ``rescore``
    ``results``, with the same ``check.py``. ``task_dir`` defaults as in
    ``rescore``."""
    check = load_check(task_dir or _recorded_task(trial_dir))
    snapshot = json.loads((trial_dir / "verifier/snapshot.json").read_text())
    return diagnostics.diagnose(
        trial_dir, getattr(check, "EXPECTED", {}), snapshot, results
    )


def check_versions(
    trial_dir: Path, task_dir: Path | None = None
) -> tuple[str, str | None]:
    """The ``check`` fingerprint ``rescore`` scores with, and the one the
    Trial recorded (``None`` for a Trial recorded without fingerprints).
    ``task_dir`` defaults as in ``rescore``."""
    record = json.loads((trial_dir / "weval.json").read_text())
    current = check_fingerprint((task_dir or _recorded_task(trial_dir)) / "check.py")
    return current, (record.get("fingerprints") or {}).get("check")


def load_check(task_dir: Path) -> ModuleType:
    """Import a Task's ``check.py`` from its file, fresh on every call."""
    spec = importlib.util.spec_from_file_location("check", task_dir / "check.py")
    assert spec and spec.loader
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    return check


def _recorded_task(trial_dir: Path) -> Path:
    return ROOT / json.loads((trial_dir / "weval.json").read_text())["task"]
