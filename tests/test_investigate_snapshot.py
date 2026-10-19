"""A connection failure during investigate/current-practices' release fetches
is recorded in the snapshot instead of raising, so the agent's submitted
findings survive and the Trial is not reduced to the error sentinel."""

import importlib.util
import urllib.error
from pathlib import Path
from types import ModuleType

SNAPSHOT_FILE = Path(__file__).parents[1] / "tasks/investigate/current-practices/snapshot.py"


def load_snapshot_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("current_practices_snapshot", SNAPSHOT_FILE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_records_a_connection_failure_instead_of_raising(monkeypatch):
    module = load_snapshot_module()

    def refuse(url, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    snapshot = module.snapshot(None)

    assert "findings" in snapshot
    for release in snapshot["latest_releases"].values():
        assert release["version"] is None
        assert release["status"] is None
        assert "connection refused" in release["error"]