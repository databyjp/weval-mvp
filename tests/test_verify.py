"""Scoring a failed snapshot: when stack preparation or ``snapshot()`` raises,
``verify.py`` scores ``{"error": <traceback>}`` instead. Every check of every
Task must then fail, with a note pointing to ``snapshot.json``.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ROOT, load_module

from weval import verify
from weval.verify import score

# The stages defined in AGENTS.md; each Task lives at tasks/<stage>/<scenario>/.
STAGES = {"build", "deploy", "resolve", "investigate"}
CHECK_FILES = sorted(ROOT.glob("tasks/*/*/check.py"))


def test_every_task_directory_is_under_a_known_stage():
    found = {p.name for p in (ROOT / "tasks").iterdir() if p.is_dir()}
    assert found <= STAGES, (
        f"unknown stage directories under tasks/: {sorted(found - STAGES)}"
    )


def task_id(check_file: Path) -> str:
    return f"{check_file.parent.parent.name}/{check_file.parent.name}"


@pytest.mark.parametrize("check_file", CHECK_FILES, ids=task_id)
def test_failed_snapshot_fails_every_check(check_file):
    check = load_module(check_file)

    results = score(check, {"error": "Traceback: weaviate unreachable"})

    assert results
    passed = [r["name"] for r in results if r["passed"]]
    assert not passed, f"checks passed on a failed snapshot: {passed}"
    assert all("snapshot failed" in r["notes"] for r in results)


def test_a_hung_stack_teardown_keeps_the_snapshot_and_score(tmp_path, monkeypatch):
    tests, app, logs = tmp_path / "tests", tmp_path / "app", tmp_path / "logs"
    for folder in (tests, app, logs):
        folder.mkdir()
    (tests / "snapshot.py").write_text(
        "def snapshot(app_url):\n    return {'up': True}\n"
    )
    (tests / "check.py").write_text(
        "def stack_up(snapshot):\n"
        '    """The stack answered."""\n'
        "    assert snapshot['up']\n\n"
        "REQUIRED = [stack_up]\nPREFERRED = []\n"
    )
    (app / "docker-compose.yaml").write_text("services: {}\n")

    def compose(*args, timeout=240):
        if args[0] == "up":
            return subprocess.CompletedProcess(args, 0, "", "")
        raise subprocess.TimeoutExpired(["docker", "compose", *args], timeout)

    monkeypatch.setattr(verify, "__file__", str(tests / "verify.py"))
    monkeypatch.setattr(verify, "APP_DIR", app)
    monkeypatch.setattr(verify, "LOG_DIR", logs)
    monkeypatch.setattr(verify, "_compose", compose)
    monkeypatch.setattr(sys, "path", list(sys.path))
    for name in ("snapshot", "check"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    try:
        verify.main()
    finally:
        for name in ("snapshot", "check"):
            sys.modules.pop(name, None)

    assert json.loads((logs / "snapshot.json").read_text()) == {"up": True}
    assert json.loads((logs / "checks.json").read_text())[0]["passed"]
    assert (logs / "reward.txt").read_text() == "1"
