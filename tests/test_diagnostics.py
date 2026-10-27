"""Diagnostics read a Trial's retained logs to explain its check results."""

import json
from pathlib import Path
from types import SimpleNamespace

from weval.diagnostics import diagnose


def write_trial(run_dir: Path, steps: list[dict], application_log: str = "") -> Path:
    trial = run_dir / "job/trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "verifier").mkdir()
    (trial / "agent/trajectory.json").write_text(json.dumps({"steps": steps}))
    (trial / "verifier/application.log").write_text(application_log)
    return trial


def write_treatment(run_dir: Path) -> None:
    pages = run_dir / "treatment/skills/weaviate-docs/pages"
    pages.mkdir(parents=True)
    (pages.parent / "SKILL.md").write_text("# Weaviate documentation\n")
    for name in ("release-notes.md", "client-libraries-python.md"):
        (pages / name).write_text(f"Source: {name}\n")


def tool_step(name: str, arguments: dict, result: str) -> dict:
    return {"source": "agent", "message": "",
            "tool_calls": [{"function_name": name, "arguments": arguments}],
            "observation": {"results": [{"content": result}]}}


NO_CHECKS = SimpleNamespace()


def test_treatment_used_records_the_skill_load_and_the_files_named(tmp_path):
    write_treatment(tmp_path)
    trial = write_trial(tmp_path, [
        tool_step("Skill", {"skill": "weaviate-docs"}, "Launching skill"),
        tool_step("Bash", {"command": "cd skills/weaviate-docs/pages; head release-notes.md"}, "Source: ..."),
    ])

    used = diagnose(trial, NO_CHECKS, {}, [])["treatment_used"]

    assert used == {"skill_loaded": True, "files_named": ["weaviate-docs/pages/release-notes.md"]}


def test_a_skill_read_as_a_file_counts_as_loaded(tmp_path):
    # Pi reads SKILL.md rather than calling a Skill tool.
    write_treatment(tmp_path)
    trial = write_trial(tmp_path, [tool_step("read", {"path": "~/.agents/skills/weaviate-docs/SKILL.md"}, "...")])

    assert diagnose(trial, NO_CHECKS, {}, [])["treatment_used"]["skill_loaded"] is True


def test_a_baseline_trial_has_no_treatment_use(tmp_path):
    trial = write_trial(tmp_path, [tool_step("Bash", {"command": "ls"}, "")])

    assert diagnose(trial, NO_CHECKS, {}, [])["treatment_used"] is None


def test_deprecations_are_split_by_who_saw_them_and_other_libraries_are_left_out(tmp_path):
    dep024 = "Dep024: You are using the `vectorizer_config` argument in `collection.config.create()`, which is deprecated."
    trial = write_trial(
        tmp_path,
        [tool_step("Bash", {"command": "python ingest.py"}, f"DeprecationWarning: {dep024}\n")],
        application_log="AuthlibDeprecationWarning: The httpx module is deprecated\n",
    )

    found = diagnose(trial, NO_CHECKS, {}, [])

    assert found["deprecations_seen"] == [dep024]
    assert found["deprecations_logged"] == []


def test_a_trial_without_a_trajectory_has_unknown_agent_facts(tmp_path):
    trial = write_trial(tmp_path, [])
    (trial / "agent/trajectory.json").unlink()

    found = diagnose(trial, NO_CHECKS, {}, [])

    assert found["deprecations_seen"] is None and found["expected_value_seen"] is None
