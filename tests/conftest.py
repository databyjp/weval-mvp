"""Shared mechanics for Task tests: loading a Task's modules and scoring a
snapshot. Scenario content (break functions, parametrize tables, expected
failure reasons) stays in each Task's own test file."""

import importlib.util
from pathlib import Path
from types import ModuleType

from weval.verify import score

ROOT = Path(__file__).parents[1]


def load_module(path: Path) -> ModuleType:
    """Import a file outside the package, such as a Task's ``check.py`` or
    ``snapshot.py``, fresh on every call."""
    name = f"{path.parent.name}_{path.stem}".replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def failures(check: ModuleType, snapshot: dict) -> dict[str, str]:
    """Each failing check's ID mapped to its failure message."""
    return {r["name"]: r["notes"] for r in score(check, snapshot) if not r["passed"]}
