"""Labels for failed checks are built from the Trial's logs, saved beside
the run, and asked again only when a request changes. No test calls the
network: the step finder (``labels._ask_steps``) and Jev (``labels._post``)
are replaced with fakes, Jev's built from a recorded response."""

import json
from pathlib import Path

import pytest

from weval import labels

ROOT = Path(__file__).parents[1]
RECORDED = json.loads((ROOT / "tests/fixtures/jev-choice-response.json").read_text())
FAILED = [
    {
        "name": "python-client-version-latest",
        "passed": False,
        "notes": "got 'Python 4.24.x'",
    },
    {"name": "findings-file", "passed": True, "notes": ""},
]
RELEASE_NOTES = "https://docs.weaviate.io/weaviate/release-notes"


def write_trial(run_dir: Path) -> Path:
    trial = run_dir / "job/trial"
    (trial / "agent").mkdir(parents=True)
    calls = [
        (
            "WebFetch",
            {"url": RELEASE_NOTES},
            "| 1.40.x | 2026-10-07 | 4.24.x | ...\n" * 20,
        ),
        (
            "ToolSearch",
            {"query": "select:WebFetch,WebSearch"},
            "Loaded WebFetch and WebSearch. " * 20,
        ),
        # The agent's own output cites a URL but shows it nothing.
        ("Write", {"content": f'{{"sources": ["{RELEASE_NOTES}x"]}}'}, "File written"),
    ]
    steps = [
        {
            "source": "agent",
            "message": "The docs list only minor lines, so check PyPI for the exact patch.",
            "tool_calls": [
                {"tool_call_id": f"c{i}", "function_name": name, "arguments": arguments}
            ],
            "observation": {"results": [{"source_call_id": f"c{i}", "content": shown}]},
        }
        for i, (name, arguments, shown) in enumerate(calls)
    ]
    (trial / "agent/trajectory.json").write_text(json.dumps({"steps": steps}))
    return trial


class FakeSteps:
    """Answers like the step finder: the write at step 3 decided the value
    and the release notes at step 1 bear on it."""

    def __init__(self):
        self.requests = []

    def __call__(self, body: dict, key: str) -> dict:
        self.requests.append(body)
        return {
            "model": "openai/gpt-6-luna",
            "checks": [
                {
                    "check": "python-client-version-latest",
                    "decision_step": 3,
                    "relevant": [{"step": 1, "kind": "source", "why": "lists 4.24.x"}],
                }
            ],
            "usage": {"cost": 0.001},
        }


class FakeJev:
    """Answers like the recorded response, choosing the first source."""

    def __init__(self):
        self.requests = []

    def __call__(self, body: dict, key: str) -> dict:
        self.requests.append(body)
        recorded = RECORDED["answers"]["verification"]
        cause = {
            **recorded,
            "choice": "followed_source",
            "probabilities": {option: 0.0 for option in labels.CAUSES},
        }
        source = {
            **recorded,
            "choice": "source_000",
            "probabilities": {
                option: 0.0 for option in body["questions"]["answer_source"]["criteria"]
            },
        }
        return {**RECORDED, "answers": {"cause": cause, "answer_source": source}}


@pytest.fixture
def steps(monkeypatch):
    fake = FakeSteps()
    monkeypatch.setattr(labels, "_ask_steps", fake)
    monkeypatch.setenv(labels.STEPS_KEY_VAR, "test-key")
    return fake


@pytest.fixture
def jev(monkeypatch, steps):
    fake = FakeJev()
    monkeypatch.setattr(labels, "_post", fake)
    monkeypatch.setenv(labels.KEY_VAR, "test-key")
    return fake


def test_each_failed_check_gets_both_labels_and_they_are_saved(tmp_path, jev):
    trial = write_trial(tmp_path)

    result = labels.label(trial, FAILED)

    assert result == {
        "labels": {
            "python-client-version-latest": {
                "model": "jev-1.14.0",
                "steps_model": "openai/gpt-6-luna",
                "decision_step": 3,
                "steps": [{"step": 1, "kind": "source", "why": "lists 4.24.x"}],
                "cause": {"choice": "followed_source", "confidence": 0.73},
                "answer_source": {"choice": RELEASE_NOTES, "confidence": 0.73},
            }
        },
        "note": None,
    }
    assert len(jev.requests) == 1
    assert (tmp_path / "labels/trial.json").exists()


def test_jev_reads_only_the_selected_steps_and_their_sources(tmp_path, jev, steps):
    labels.label(write_trial(tmp_path), FAILED)

    # The step finder reads the whole trace and may name only failed checks.
    trace = steps.requests[0]["messages"][1]["content"]
    assert "### Step 2 (agent)" in trace
    schema = steps.requests[0]["response_format"]["json_schema"]["schema"]
    check = schema["properties"]["checks"]["items"]["properties"]["check"]
    assert check["enum"] == ["python-client-version-latest"]
    # Jev reads steps 1 and 3, not the ToolSearch at step 2, nor the reasons.
    shown = jev.requests[0]["state"]["steps"]
    assert [text.split("\n")[:2] for text in shown] == [
        ["[source]", "### Step 1 (agent)"],
        ["[decision]", "### Step 3 (agent)"],
    ]
    assert "lists 4.24.x" not in json.dumps(jev.requests[0])
    options = jev.requests[0]["questions"]["answer_source"]["criteria"]
    assert list(options.values()) == [
        f"{RELEASE_NOTES} (shown in step 1)",
        labels.OWN_KNOWLEDGE,
    ]


def test_steps_missing_from_the_trace_are_dropped(tmp_path, jev, steps, monkeypatch):
    def finder(body: dict, key: str) -> dict:
        answer = FakeSteps()(body, key)
        answer["checks"][0]["decision_step"] = 99
        answer["checks"][0]["relevant"][0]["step"] = 0
        return answer

    monkeypatch.setattr(labels, "_ask_steps", finder)

    found = labels.label(write_trial(tmp_path), FAILED)["labels"]

    assert found["python-client-version-latest"]["decision_step"] is None
    assert found["python-client-version-latest"]["steps"] == []
    assert jev.requests[0]["state"]["steps"] == []


def test_pi_pages_and_claude_code_skills_count_for_their_source(tmp_path):
    # Pi's fetch_content shows only titles and stores the pages; the agent
    # reads page 1 by responseId. Claude Code's Skill call shows only
    # "Launching skill"; the skill's text is the next user message.
    page = "https://docs.weaviate.io/weaviate/manage-collections/vector-config"
    listing = (
        "## Fetched URLs\n\n- Collections (9000 chars)\n- Vector config (9636 chars)\n"
        + "x" * 200
        + '\nUse get_search_content({ responseId: "r1", urlIndex: 0 }) to read.'
    )
    skill_text = (
        "Base directory for this skill: /logs/agent/sessions/skills/best\n\n"
        "# Best practices\nUse vector_config. " * 10
    )
    skills = tmp_path / "skills/best"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(skill_text)
    steps = [
        {
            "source": "agent",
            "tool_calls": [
                {
                    "tool_call_id": "c0",
                    "function_name": "fetch_content",
                    "arguments": {"urls": ["https://docs.weaviate.io/x", page]},
                },
                {
                    "tool_call_id": "c1",
                    "function_name": "get_search_content",
                    "arguments": {"responseId": "r1", "urlIndex": 1},
                },
                {
                    "tool_call_id": "c2",
                    "function_name": "Skill",
                    "arguments": {"skill": "best"},
                },
            ],
            "observation": {
                "results": [
                    {"source_call_id": "c0", "content": listing},
                    {"source_call_id": "c1", "content": "# Vector config\n" * 20},
                    {"source_call_id": "c2", "content": "Launching skill: best"},
                ]
            },
        },
        {"source": "user", "message": skill_text},
    ]

    names = labels._source_names(labels._numbered(steps), tmp_path / "skills")

    # The unread page is not a source: the agent saw only its title.
    assert names == {1: [page], 2: ["best/SKILL.md"]}


def test_a_trial_whose_snapshot_failed_is_not_labelled(tmp_path, jev):
    trial = write_trial(tmp_path)
    (trial / "verifier").mkdir()
    (trial / "verifier/snapshot.json").write_text(
        json.dumps({"error": "Traceback ...", "error_stage": "stack"})
    )

    assert labels.label(trial, FAILED) == {
        "labels": {},
        "note": "unlabelled: the snapshot failed",
    }
    assert jev.requests == []


def test_a_saved_label_is_reused_until_the_request_changes(tmp_path, jev, steps):
    trial = write_trial(tmp_path)
    labels.label(trial, FAILED)

    assert labels.label(trial, FAILED)["labels"]
    assert (len(steps.requests), len(jev.requests)) == (1, 1)

    rescored = [{**FAILED[0], "notes": "got 'Python 4.24'"}]
    labels.label(trial, rescored)
    assert (len(steps.requests), len(jev.requests)) == (2, 2)


def test_without_the_keys_or_a_call_only_saved_labels_are_returned(
    tmp_path, jev, steps, monkeypatch
):
    trial = write_trial(tmp_path)

    assert labels.label(trial, FAILED, call=False) == {
        "labels": {},
        "note": "unlabelled (not requested): python-client-version-latest",
    }
    monkeypatch.delenv(labels.KEY_VAR)
    assert labels.label(trial, FAILED)["note"] == (
        f"unlabelled ({labels.KEY_VAR} not set): python-client-version-latest"
    )
    assert steps.requests == jev.requests == []


def test_a_run_is_labelled_after_scoring_and_a_failure_does_not_raise(
    tmp_path, monkeypatch, capsys
):
    from weval.run import label_run

    trial = write_trial(tmp_path)
    (trial / "weval.json").write_text(json.dumps({"checks": FAILED}))
    monkeypatch.delenv(labels.STEPS_KEY_VAR, raising=False)
    monkeypatch.delenv(labels.KEY_VAR, raising=False)

    label_run(tmp_path)

    assert (
        f"unlabelled ({labels.STEPS_KEY_VAR} and {labels.KEY_VAR} not set)"
        in capsys.readouterr().out
    )
