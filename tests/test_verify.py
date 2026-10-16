"""Scoring a failed snapshot: when stack preparation or ``snapshot()`` raises,
``verify.py`` scores ``{"error": <traceback>}`` instead. Every check of every
Task must then fail, with a note pointing to ``snapshot.json``.
"""

import importlib.util
from pathlib import Path

import pytest

from weval.verify import score

ROOT = Path(__file__).parents[1]


# The stages defined in AGENTS.md; each Task lives at tasks/<stage>/<scenario>/.
STAGES = {"build", "deploy", "resolve", "investigate"}
CHECK_FILES = sorted(ROOT.glob("tasks/*/*/check.py"))


def test_every_task_directory_is_under_a_known_stage():
    found = {p.name for p in (ROOT / "tasks").iterdir() if p.is_dir()}
    assert found <= STAGES, f"unknown stage directories under tasks/: {sorted(found - STAGES)}"


@pytest.mark.parametrize("check_file", CHECK_FILES, ids=lambda p: f"{p.parent.parent.name}/{p.parent.name}")
def test_failed_snapshot_fails_every_check(check_file):
    spec = importlib.util.spec_from_file_location(f"{check_file.parent.name}_check", check_file)
    assert spec and spec.loader
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)

    results = score(check, {"error": "Traceback: weaviate unreachable"})

    assert results
    passed = [r["name"] for r in results if r["passed"]]
    assert not passed, f"checks passed on a failed snapshot: {passed}"
    assert all("snapshot failed" in r["notes"] for r in results)
