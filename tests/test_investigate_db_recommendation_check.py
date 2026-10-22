"""Calibrate investigate/db-recommendation: the Oracle snapshot passes,
each broken variant fails exactly the check aimed at it, and nothing the
agent sees names Weaviate.

``fixtures/investigate-db-recommendation-oracle-snapshot.json`` is a real
snapshot retained from a local Oracle Trial.
"""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from weval.run import SHARED_COMPOSE, SHARED_INSTRUCTIONS, compose_overlays
from weval.verify import score

ROOT = Path(__file__).parents[1]
TASK = ROOT / "tasks/investigate/db-recommendation"
ORACLE = json.loads((ROOT / "tests/fixtures/investigate-db-recommendation-oracle-snapshot.json").read_text())

_spec = importlib.util.spec_from_file_location("investigate_db_recommendation_check", TASK / "check.py")
assert _spec and _spec.loader
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def failures(snapshot: dict) -> dict[str, str]:
    return {r["name"]: r["notes"] for r in score(check, snapshot) if not r["passed"]}


def missing_file(s: dict) -> None:
    s["recommendation"] = {"text": None, "error": "/app/RECOMMENDATION.md does not exist"}


def blank_file(s: dict) -> None:
    s["recommendation"]["text"] = "\n  \n"


def test_oracle_passes_every_check():
    assert failures(ORACLE) == {}


@pytest.mark.parametrize(
    ("break_snapshot", "failing_check", "reason"),
    [
        (missing_file, "recommendation-file", "does not exist"),
        (blank_file, "recommendation-file", "only whitespace"),
    ],
)
def test_broken_variant_fails_only_its_check(break_snapshot, failing_check, reason):
    snapshot = copy.deepcopy(ORACLE)
    break_snapshot(snapshot)
    failed = failures(snapshot)
    assert list(failed) == [failing_check]
    assert reason in failed[failing_check]


def test_agent_visible_files_do_not_name_weaviate():
    # The question is whether the agent suggests Weaviate unprompted. The
    # agent sees the packaged prompt, the environment, and the settings the
    # Compose overlays give it (not the overlay files themselves).
    assert compose_overlays(TASK) == [SHARED_COMPOSE]
    assert "WEAVIATE_" not in SHARED_COMPOSE.read_text()
    visible = [TASK / "instruction.md", SHARED_INSTRUCTIONS,
               *(TASK / "prompts").glob("*.md"), *(TASK / "environment").rglob("*")]
    named = [p.relative_to(ROOT) for p in visible if p.is_file() and "weaviate" in p.read_text().lower()]
    assert named == []
