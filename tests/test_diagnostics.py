"""Diagnostics read a Trial's retained logs to explain its check results."""

import json
from pathlib import Path
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


NO_CHECKS: dict = {}


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


def test_expected_value_seen_reports_each_failed_check_with_an_expected_value(tmp_path):
    trial = write_trial(tmp_path, [
        {"source": "user", "message": "Find the latest versions."},
        tool_step("Bash", {"command": "head client-libraries-python.md"},
                  "The latest Python client is version `v4.24.1`."),
        # The agent's own output is not what it was shown.
        tool_step("Write", {"content": "Weaviate 1.40.2"}, "File written"),
    ])
    expected = {
        "client": lambda snapshot: snapshot["client"],
        "server": lambda snapshot: snapshot["server"],
        "unknown": lambda snapshot: snapshot["missing"],
    }
    results = [{"name": name, "passed": False} for name in ("client", "server", "unknown", "no-expected-value")]
    results.append({"name": "passed-check", "passed": True})

    found = diagnose(trial, expected, {"client": "4.24.1", "server": "1.40.2"}, results)

    assert found["expected_value_seen"] == [
        {"check": "client", "expected": "4.24.1", "seen": True},
        {"check": "server", "expected": "1.40.2", "seen": False},
    ]


def test_an_expected_value_must_match_exactly(tmp_path):
    trial = write_trial(tmp_path, [tool_step("Bash", {"command": "pip index"}, "weaviate-client 4.24.10, 14.24.1")])
    expected = {"client": lambda snapshot: "4.24.1"}

    [item] = diagnose(trial, expected, {}, [{"name": "client", "passed": False}])["expected_value_seen"]

    assert item["seen"] is False
