"""Jev labels for failed checks are built from the Trial's logs, saved beside
the run, and asked again only when the request changes. No test calls the
network: ``labels._post`` is replaced with a fake built from a recorded
response."""

import json
from pathlib import Path

import pytest

from weval import labels

ROOT = Path(__file__).parents[1]
RECORDED = json.loads((ROOT / "tests/fixtures/jev-choice-response.json").read_text())
FAILED = [{"name": "python-client-version-latest", "passed": False, "notes": "got 'Python 4.24.x'"},
          {"name": "findings-file", "passed": True, "notes": ""}]
RELEASE_NOTES = "https://docs.weaviate.io/weaviate/release-notes"


def write_trial(run_dir: Path) -> Path:
    trial = run_dir / "job/trial"
    (trial / "agent").mkdir(parents=True)
    calls = [
        ("WebFetch", {"url": RELEASE_NOTES}, "| 1.40.x | 2026-10-07 | 4.24.x | ...\n" * 20),
        ("ToolSearch", {"query": "select:WebFetch,WebSearch"}, "Loaded WebFetch and WebSearch. " * 20),
        # The agent's own output cites a URL but shows it nothing.
        ("Write", {"content": f'{{"sources": ["{RELEASE_NOTES}x"]}}'}, "File written"),
    ]
    steps = [{"source": "agent", "message": "The docs list only minor lines, so check PyPI for the exact patch.",
              "tool_calls": [{"tool_call_id": f"c{i}", "function_name": name, "arguments": arguments}],
              "observation": {"results": [{"source_call_id": f"c{i}", "content": shown}]}}
             for i, (name, arguments, shown) in enumerate(calls)]
    (trial / "agent/trajectory.json").write_text(json.dumps({"steps": steps}))
    return trial


class FakeJev:
    """Answers like the recorded response, choosing the first source."""

    def __init__(self):
        self.requests = []

    def __call__(self, body: dict, key: str) -> dict:
        self.requests.append(body)
        verification = RECORDED["answers"]["verification"]
        source = {**verification, "choice": "source_000",
                  "probabilities": {option: 0.0 for option in body["questions"]["answer_source"]["criteria"]}}
        return {**RECORDED, "answers": {"answer_source": source, "verification": verification}}


@pytest.fixture
def jev(monkeypatch):
    fake = FakeJev()
    monkeypatch.setattr(labels, "_post", fake)
    monkeypatch.setenv(labels.KEY_VAR, "test-key")
    return fake


def test_each_failed_check_gets_both_labels_and_they_are_saved(tmp_path, jev):
    trial = write_trial(tmp_path)

    result = labels.label(trial, FAILED)

    assert result == {"labels": {"python-client-version-latest": {
        "model": "jev-1.14.0",
        "answer_source": {"choice": RELEASE_NOTES, "confidence": 0.73},
        "verification": {"choice": "deferred_to_user", "confidence": 0.73},
    }}, "note": None}
    assert len(jev.requests) == 1
    assert (tmp_path / "labels/trial.json").exists()


def test_sources_are_what_the_agent_was_shown(tmp_path, jev):
    labels.label(write_trial(tmp_path), FAILED)

    options = jev.requests[0]["questions"]["answer_source"]["criteria"]
    names = [description.split("\n")[0] for description in options.values()]
    assert names == [RELEASE_NOTES, labels.OWN_KNOWLEDGE]


def test_a_saved_label_is_reused_until_the_request_changes(tmp_path, jev):
    trial = write_trial(tmp_path)
    labels.label(trial, FAILED)

    assert labels.label(trial, FAILED)["labels"]
    assert len(jev.requests) == 1

    rescored = [{**FAILED[0], "notes": "got 'Python 4.24'"}]
    labels.label(trial, rescored)
    assert len(jev.requests) == 2


def test_without_the_key_or_a_call_only_saved_labels_are_returned(tmp_path, jev, monkeypatch):
    trial = write_trial(tmp_path)

    assert labels.label(trial, FAILED, call=False) == {
        "labels": {}, "note": "unlabelled (not requested): python-client-version-latest"}
    monkeypatch.delenv(labels.KEY_VAR)
    assert labels.label(trial, FAILED)["note"] == (
        f"unlabelled ({labels.KEY_VAR} is not set): python-client-version-latest")
    assert jev.requests == []


def test_a_run_is_labelled_after_scoring_and_a_failure_does_not_raise(tmp_path, monkeypatch, capsys):
    from weval.run import label_run

    trial = write_trial(tmp_path)
    (trial / "weval.json").write_text(json.dumps({"checks": FAILED}))
    monkeypatch.delenv(labels.KEY_VAR, raising=False)

    label_run(tmp_path)

    assert f"unlabelled ({labels.KEY_VAR} is not set)" in capsys.readouterr().out
