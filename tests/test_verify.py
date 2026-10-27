"""Scoring a failed snapshot: when stack preparation or ``snapshot()`` raises,
``verify.py`` scores ``{"error": <traceback>}`` instead. Every check of every
Task and prompt variant must then fail, with a note pointing to ``snapshot.json``.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import ROOT, load_module

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

    for prompt_variant in getattr(check, "PROMPT_VARIANT_REQUIRED", {"default": []}):
        results = score(
            check,
            {
                "error": "Traceback: weaviate unreachable",
                "prompt_variant": prompt_variant,
            },
        )

        assert results
        passed = [r["name"] for r in results if r["passed"]]
        assert not passed, (
            f"{prompt_variant}: checks passed on a failed snapshot: {passed}"
        )
        assert all("snapshot failed" in r["notes"] for r in results)


@pytest.mark.parametrize("check_file", CHECK_FILES, ids=task_id)
def test_variant_check_lists_name_exactly_the_tasks_prompt_variants(check_file):
    check = load_module(check_file)
    prompts = {p.stem for p in (check_file.parent / "prompts").glob("*.md")}
    if not prompts:
        assert not hasattr(check, "PROMPT_VARIANT_REQUIRED") and not hasattr(
            check, "PROMPT_VARIANT_PREFERRED"
        )
        return

    assert set(check.PROMPT_VARIANT_REQUIRED) == {"default"} | prompts
    assert set(check.PROMPT_VARIANT_PREFERRED) == {"default"} | prompts


def test_score_adds_the_snapshot_prompt_variants_checks():
    def shared(snapshot):
        """Shared."""

    def legal_only(snapshot):
        """legal-archive only."""

    def legal_preferred(snapshot):
        """legal-archive, preferred."""

    check = SimpleNamespace(
        REQUIRED=[shared],
        PREFERRED=[],
        PROMPT_VARIANT_REQUIRED={"default": [], "legal-archive": [legal_only]},
        PROMPT_VARIANT_PREFERRED={"default": [], "legal-archive": [legal_preferred]},
    )

    def scored(snapshot):
        return [(r["name"], r["required"]) for r in score(check, snapshot)]

    assert scored({"prompt_variant": "legal-archive"}) == [
        ("shared", True),
        ("legal-only", True),
        ("legal-preferred", False),
    ]
    assert scored({"prompt_variant": "default"}) == [("shared", True)]
    # A snapshot without prompt_variant scores as default.
    assert scored({}) == [("shared", True)]
